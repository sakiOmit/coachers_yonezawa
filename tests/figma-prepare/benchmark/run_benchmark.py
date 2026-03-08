#!/usr/bin/env python3
"""Comprehensive benchmark runner for figma-prepare analysis pipeline.

Runs Phase 1 (structure analysis), Phase 2 Stage A (grouping detection),
Phase 3 (semantic rename), and Phase 4 (Auto Layout inference) on Figma
metadata fixtures and produces detailed reports.

Accepts XML or JSON fixture files (auto-detected by load_metadata).

Usage:
    python run_benchmark.py fixture1.xml [fixture2.json ...]
    python run_benchmark.py --all              # run on all fixtures in data/
    python run_benchmark.py --results-dir DIR  # override results output dir

Results are written to ``results/`` (YAML + JSON).
"""

import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BENCHMARK_DIR, 'results')
DATA_DIR = os.path.join(BENCHMARK_DIR, 'data')

LIB_DIR = os.path.join(
    BENCHMARK_DIR, '..', '..', '..',
    '.claude', 'skills', 'figma-prepare', 'lib',
)
sys.path.insert(0, os.path.abspath(LIB_DIR))

# Raise recursion limit for deeply nested Figma trees
sys.setrecursionlimit(5000)

# ---------------------------------------------------------------------------
# figma_utils imports
# ---------------------------------------------------------------------------
from figma_utils.metadata import load_metadata, get_root_node, is_unnamed  # noqa: E402
from figma_utils.geometry import resolve_absolute_coords, get_bbox, filter_visible_children  # noqa: E402
from figma_utils.structure_analysis import count_nodes, detect_grouping_candidates_simple, run_structure_analysis  # noqa: E402
from figma_utils.grouping_engine import detect_grouping_candidates, walk_and_detect  # noqa: E402
from figma_utils.grouping_walker import _is_protected_node  # noqa: E402
from figma_utils.semantic_rename import collect_renames, infer_name_with_confidence  # noqa: E402
from figma_utils.detection import detect_en_jp_label_pairs  # noqa: E402
from figma_utils.autolayout import walk_and_infer  # noqa: E402
from figma_utils.scoring import structure_hash  # noqa: E402
from figma_utils.constants import UNNAMED_RE, FLAT_THRESHOLD, DEEP_NESTING_THRESHOLD  # noqa: E402
from figma_utils.enrichment import generate_enriched_table  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_yaml_str(s):
    """Quote a string for YAML output."""
    if not s:
        return '""'
    if any(c in s for c in ':{}[],"\'#&*!|>%@`'):
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


def _count_all_nodes(node):
    """Count total visible nodes recursively."""
    if node.get('visible') == False:
        return 0
    total = 1
    for child in node.get('children', []):
        total += _count_all_nodes(child)
    return total


def _collect_node_types(node, counter=None):
    """Collect node type distribution."""
    if counter is None:
        counter = Counter()
    if node.get('visible') == False:
        return counter
    counter[node.get('type', 'UNKNOWN')] += 1
    for child in node.get('children', []):
        _collect_node_types(child, counter)
    return counter


def _collect_depth_histogram(node, depth=0, histogram=None):
    """Collect node count per depth level."""
    if histogram is None:
        histogram = Counter()
    if node.get('visible') == False:
        return histogram
    histogram[depth] += 1
    for child in node.get('children', []):
        _collect_depth_histogram(child, depth + 1, histogram)
    return histogram


def _collect_structure_hashes(node, hashes=None):
    """Collect structure hashes for pattern analysis."""
    if hashes is None:
        hashes = Counter()
    if node.get('visible') == False:
        return hashes
    children = filter_visible_children(node)
    if children:
        h = structure_hash(node)
        hashes[h] += 1
    for child in children:
        _collect_structure_hashes(child, hashes)
    return hashes


def _count_en_jp_pairs(node):
    """Count EN+JP label pairs recursively."""
    if node.get('visible') == False:
        return 0
    count = 0
    children = filter_visible_children(node)
    if children:
        pairs = detect_en_jp_label_pairs(children)
        count += len(pairs)
    for child in children:
        count += _count_en_jp_pairs(child)
    return count


def _collect_flat_sections(node, results=None):
    """Collect sections with more children than FLAT_THRESHOLD."""
    if results is None:
        results = []
    if node.get('visible') == False:
        return results
    children = filter_visible_children(node)
    ntype = node.get('type', '')
    if ntype in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION') and len(children) > FLAT_THRESHOLD:
        results.append({
            'name': node.get('name', ''),
            'id': node.get('id', ''),
            'child_count': len(children),
            'excess': len(children) - FLAT_THRESHOLD,
        })
    for child in children:
        _collect_flat_sections(child, results)
    return results


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

def run_phase1(fixture_path):
    """Run Phase 1 structure analysis.

    Returns parsed result dict.
    """
    result_json = run_structure_analysis(fixture_path)
    return json.loads(result_json)


def run_phase2_stage_a(fixture_path):
    """Run Phase 2 Stage A grouping detection.

    Returns dict with candidates list and method breakdown.
    """
    data = load_metadata(fixture_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)

    candidates = walk_and_detect(root)

    # Deduplicate
    from figma_utils.comparison import deduplicate_candidates
    candidates = deduplicate_candidates(candidates, root_id=root.get('id', ''))

    # Method breakdown
    method_counts = Counter()
    method_scores = defaultdict(list)
    for c in candidates:
        method = c.get('method', 'unknown')
        method_counts[method] += 1
        if 'score' in c:
            method_scores[method].append(c['score'])

    method_summary = {}
    for m in sorted(method_counts.keys()):
        entry = {'count': method_counts[m]}
        if method_scores[m]:
            scores = method_scores[m]
            entry['avg_score'] = round(sum(scores) / len(scores), 4)
            entry['min_score'] = round(min(scores), 4)
            entry['max_score'] = round(max(scores), 4)
        method_summary[m] = entry

    # Collect parent distribution
    parent_dist = Counter(c.get('parent_name', 'root') for c in candidates)

    return {
        'total_candidates': len(candidates),
        'method_breakdown': method_summary,
        'parent_distribution': dict(parent_dist.most_common(20)),
        'candidates': candidates,
    }


def run_phase3(fixture_path):
    """Run Phase 3 semantic rename.

    Returns dict with renames and confidence distribution.
    """
    data = load_metadata(fixture_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)

    renames = collect_renames(root)

    # Confidence distribution
    conf_buckets = {
        'high (80-100)': 0,
        'medium (50-79)': 0,
        'low (20-49)': 0,
        'very_low (0-19)': 0,
    }
    method_counts = Counter()
    for r in renames.values():
        conf = r.get('confidence', 50)
        method = r.get('inference_method', 'unknown')
        method_counts[method] += 1
        if conf >= 80:
            conf_buckets['high (80-100)'] += 1
        elif conf >= 50:
            conf_buckets['medium (50-79)'] += 1
        elif conf >= 20:
            conf_buckets['low (20-49)'] += 1
        else:
            conf_buckets['very_low (0-19)'] += 1

    # Prefix distribution (e.g., heading-, btn-, card-)
    prefix_dist = Counter()
    for r in renames.values():
        name = r.get('new_name', '')
        parts = name.split('-')
        if len(parts) >= 2:
            prefix_dist[parts[0] + '-'] += 1
        else:
            prefix_dist[name] += 1

    # EN+JP pair count
    en_jp_count = _count_en_jp_pairs(root)

    return {
        'total_renames': len(renames),
        'confidence_distribution': conf_buckets,
        'method_distribution': dict(method_counts.most_common()),
        'prefix_distribution': dict(prefix_dist.most_common(20)),
        'en_jp_pairs_detected': en_jp_count,
        'renames': renames,
    }


def run_phase4(fixture_path):
    """Run Phase 4 Auto Layout inference.

    Returns dict with layout results and direction distribution.
    """
    data = load_metadata(fixture_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)

    results = walk_and_infer(root)

    # Direction distribution
    dir_dist = Counter(r['layout']['direction'] for r in results)

    # Confidence distribution
    conf_dist = Counter()
    for r in results:
        conf = r['layout'].get('confidence', 'unknown')
        conf_dist[conf] += 1

    # Source distribution (geometry vs name-hint)
    source_dist = Counter(r.get('source', 'unknown') for r in results)

    return {
        'total_frames': len(results),
        'direction_distribution': dict(dir_dist.most_common()),
        'confidence_distribution': dict(conf_dist.most_common()),
        'source_distribution': dict(source_dist.most_common()),
        'results': results,
    }


# ---------------------------------------------------------------------------
# Tree structure analysis (supplementary)
# ---------------------------------------------------------------------------

def analyze_tree_structure(fixture_path):
    """Supplementary tree structure analysis not covered by Phase 1."""
    data = load_metadata(fixture_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)

    root_bb = get_bbox(root)
    page_width = root_bb.get('w', 0) if root_bb else 0
    page_height = root_bb.get('h', 0) if root_bb else 0

    # Node type distribution
    type_dist = _collect_node_types(root)

    # Depth histogram
    depth_hist = _collect_depth_histogram(root)

    # Structure hash distribution (for pattern richness)
    hash_dist = _collect_structure_hashes(root)
    repeated_hashes = {h: c for h, c in hash_dist.items() if c >= 3}

    # Flat sections detail
    flat_sections = _collect_flat_sections(root)

    # Root children summary
    root_children = filter_visible_children(root)
    root_child_summary = []
    for i, child in enumerate(root_children):
        child_bb = get_bbox(child)
        child_count = _count_all_nodes(child)
        root_child_summary.append({
            'index': i,
            'name': child.get('name', ''),
            'type': child.get('type', ''),
            'y': child_bb.get('y', 0) if child_bb else 0,
            'height': child_bb.get('h', 0) if child_bb else 0,
            'descendant_count': child_count,
        })

    return {
        'page_dimensions': {'width': page_width, 'height': page_height},
        'root_children_count': len(root_children),
        'node_type_distribution': dict(type_dist.most_common()),
        'depth_histogram': {str(k): v for k, v in sorted(depth_hist.items())},
        'max_depth': max(depth_hist.keys()) if depth_hist else 0,
        'repeated_structure_hashes': len(repeated_hashes),
        'total_unique_hashes': len(hash_dist),
        'flat_sections_detail': flat_sections[:10],  # top 10
        'root_children_summary': root_child_summary[:30],  # first 30
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(fixture_path, results_dir=None):
    """Run all phases and generate a comprehensive report.

    Returns:
        dict: Complete benchmark result.
    """
    if results_dir is None:
        results_dir = RESULTS_DIR
    os.makedirs(results_dir, exist_ok=True)

    basename = os.path.splitext(os.path.basename(fixture_path))[0]
    print(f"\n{'='*70}")
    print(f"  BENCHMARK: {basename}")
    print(f"{'='*70}")

    report = {
        'fixture': os.path.basename(fixture_path),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'phases': {},
        'timings': {},
    }

    # --- Tree Structure ---
    print("\n  [1/5] Tree structure analysis...")
    t0 = time.time()
    tree_info = analyze_tree_structure(fixture_path)
    report['tree_structure'] = tree_info
    report['timings']['tree_analysis'] = round(time.time() - t0, 3)
    print(f"        Page: {tree_info['page_dimensions']['width']}x{tree_info['page_dimensions']['height']}px")
    print(f"        Root children: {tree_info['root_children_count']}")
    print(f"        Max depth: {tree_info['max_depth']}")

    # --- Phase 1 ---
    print("\n  [2/5] Phase 1: Structure quality analysis...")
    t0 = time.time()
    phase1 = run_phase1(fixture_path)
    report['phases']['phase1'] = phase1
    report['timings']['phase1'] = round(time.time() - t0, 3)
    print(f"        Score: {phase1['score']} ({phase1['grade']})")
    print(f"        Total nodes: {phase1['metrics']['total_nodes']}")
    print(f"        Unnamed: {phase1['metrics']['unnamed_nodes']} ({phase1['metrics']['unnamed_rate_pct']}%)")
    print(f"        Flat sections: {phase1['metrics']['flat_sections']}")
    print(f"        Deep nesting: {phase1['metrics']['deep_nesting_count']}")
    print(f"        Hidden nodes: {phase1['metrics']['hidden_nodes']}")
    print(f"        Off-canvas: {phase1['metrics']['off_canvas_nodes']}")
    print(f"        Recommendation: {phase1['recommendation']}")
    print(f"        Score breakdown:")
    for k, v in phase1['score_breakdown'].items():
        print(f"          {k}: -{v}")

    # --- Phase 2 Stage A ---
    print("\n  [3/5] Phase 2 Stage A: Grouping detection...")
    t0 = time.time()
    phase2 = run_phase2_stage_a(fixture_path)
    # Remove full candidates list from report (too large for YAML)
    candidates_full = phase2.pop('candidates')
    report['phases']['phase2_stage_a'] = phase2
    report['timings']['phase2_stage_a'] = round(time.time() - t0, 3)
    print(f"        Total candidates: {phase2['total_candidates']}")
    print(f"        Method breakdown:")
    for method, info in sorted(phase2['method_breakdown'].items()):
        score_str = f" (avg={info['avg_score']:.3f})" if 'avg_score' in info else ""
        print(f"          {method}: {info['count']}{score_str}")
    print(f"        Parent distribution (top 5):")
    for parent, count in list(phase2['parent_distribution'].items())[:5]:
        print(f"          {parent}: {count}")

    # --- Phase 3 ---
    print("\n  [4/5] Phase 3: Semantic rename...")
    t0 = time.time()
    phase3 = run_phase3(fixture_path)
    # Remove full renames from report
    renames_full = phase3.pop('renames')
    report['phases']['phase3'] = phase3
    report['timings']['phase3'] = round(time.time() - t0, 3)
    print(f"        Total renames: {phase3['total_renames']}")
    print(f"        EN+JP pairs: {phase3['en_jp_pairs_detected']}")
    print(f"        Confidence distribution:")
    for bucket, count in phase3['confidence_distribution'].items():
        pct = round(count / max(phase3['total_renames'], 1) * 100, 1)
        print(f"          {bucket}: {count} ({pct}%)")
    print(f"        Inference method distribution:")
    for method, count in phase3['method_distribution'].items():
        print(f"          {method}: {count}")
    print(f"        Top name prefixes:")
    for prefix, count in list(phase3['prefix_distribution'].items())[:10]:
        print(f"          {prefix}: {count}")

    # --- Phase 4 ---
    print("\n  [5/5] Phase 4: Auto Layout inference...")
    t0 = time.time()
    phase4 = run_phase4(fixture_path)
    # Remove full results from report
    autolayout_full = phase4.pop('results')
    report['phases']['phase4'] = phase4
    report['timings']['phase4'] = round(time.time() - t0, 3)
    print(f"        Total frames analyzed: {phase4['total_frames']}")
    print(f"        Direction distribution:")
    for d, count in phase4['direction_distribution'].items():
        print(f"          {d}: {count}")
    print(f"        Confidence distribution:")
    for c, count in phase4['confidence_distribution'].items():
        print(f"          {c}: {count}")

    # --- Summary ---
    total_time = sum(report['timings'].values())
    report['timings']['total'] = round(total_time, 3)
    print(f"\n  Total time: {total_time:.3f}s")

    # --- Write results ---
    result_json_path = os.path.join(results_dir, f'{basename}-benchmark.json')
    with open(result_json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    result_yaml_path = os.path.join(results_dir, f'{basename}-benchmark.yaml')
    _write_yaml_report(report, result_yaml_path)

    print(f"\n  Results written to:")
    print(f"    JSON: {result_json_path}")
    print(f"    YAML: {result_yaml_path}")

    # Write detailed outputs (candidates, renames) as separate files
    detail_dir = os.path.join(results_dir, basename)
    os.makedirs(detail_dir, exist_ok=True)

    candidates_path = os.path.join(detail_dir, 'grouping-candidates.json')
    with open(candidates_path, 'w', encoding='utf-8') as f:
        json.dump(candidates_full, f, indent=2, ensure_ascii=False, default=str)

    renames_path = os.path.join(detail_dir, 'renames.json')
    with open(renames_path, 'w', encoding='utf-8') as f:
        json.dump(renames_full, f, indent=2, ensure_ascii=False, default=str)

    autolayout_path = os.path.join(detail_dir, 'autolayout.json')
    with open(autolayout_path, 'w', encoding='utf-8') as f:
        json.dump(autolayout_full, f, indent=2, ensure_ascii=False, default=str)

    return report


def _write_yaml_report(report, path):
    """Write a human-readable YAML summary report."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# Figma Prepare Benchmark Report\n')
        f.write(f'# Generated: {report["timestamp"]}\n\n')

        f.write(f'fixture: {_safe_yaml_str(report["fixture"])}\n\n')

        # Tree structure
        ts = report.get('tree_structure', {})
        dims = ts.get('page_dimensions', {})
        f.write('tree_structure:\n')
        f.write(f'  page_width: {dims.get("width", 0)}\n')
        f.write(f'  page_height: {dims.get("height", 0)}\n')
        f.write(f'  root_children: {ts.get("root_children_count", 0)}\n')
        f.write(f'  max_depth: {ts.get("max_depth", 0)}\n')
        f.write(f'  repeated_patterns: {ts.get("repeated_structure_hashes", 0)}\n')
        f.write(f'  unique_hashes: {ts.get("total_unique_hashes", 0)}\n')

        # Node type distribution
        ntd = ts.get('node_type_distribution', {})
        if ntd:
            f.write('  node_types:\n')
            for ntype, count in sorted(ntd.items(), key=lambda x: -x[1]):
                f.write(f'    {ntype}: {count}\n')

        # Phase 1
        p1 = report.get('phases', {}).get('phase1', {})
        f.write('\nphase1_quality:\n')
        f.write(f'  score: {p1.get("score", 0)}\n')
        f.write(f'  grade: {p1.get("grade", "?")}\n')
        f.write(f'  recommendation: {_safe_yaml_str(p1.get("recommendation", ""))}\n')
        metrics = p1.get('metrics', {})
        f.write('  metrics:\n')
        for k, v in sorted(metrics.items()):
            f.write(f'    {k}: {v}\n')
        breakdown = p1.get('score_breakdown', {})
        f.write('  score_breakdown:\n')
        for k, v in sorted(breakdown.items()):
            f.write(f'    {k}: {v}\n')

        # Phase 2
        p2 = report.get('phases', {}).get('phase2_stage_a', {})
        f.write('\nphase2_grouping:\n')
        f.write(f'  total_candidates: {p2.get("total_candidates", 0)}\n')
        mb = p2.get('method_breakdown', {})
        if mb:
            f.write('  methods:\n')
            for method, info in sorted(mb.items()):
                f.write(f'    {method}:\n')
                f.write(f'      count: {info["count"]}\n')
                if 'avg_score' in info:
                    f.write(f'      avg_score: {info["avg_score"]}\n')
                    f.write(f'      min_score: {info["min_score"]}\n')
                    f.write(f'      max_score: {info["max_score"]}\n')

        # Phase 3
        p3 = report.get('phases', {}).get('phase3', {})
        f.write('\nphase3_rename:\n')
        f.write(f'  total_renames: {p3.get("total_renames", 0)}\n')
        f.write(f'  en_jp_pairs: {p3.get("en_jp_pairs_detected", 0)}\n')
        cd = p3.get('confidence_distribution', {})
        if cd:
            f.write('  confidence:\n')
            for bucket, count in cd.items():
                f.write(f'    {_safe_yaml_str(bucket)}: {count}\n')
        md = p3.get('method_distribution', {})
        if md:
            f.write('  methods:\n')
            for method, count in md.items():
                f.write(f'    {method}: {count}\n')
        pd = p3.get('prefix_distribution', {})
        if pd:
            f.write('  top_prefixes:\n')
            for prefix, count in list(pd.items())[:15]:
                f.write(f'    {_safe_yaml_str(prefix)}: {count}\n')

        # Phase 4
        p4 = report.get('phases', {}).get('phase4', {})
        f.write('\nphase4_autolayout:\n')
        f.write(f'  total_frames: {p4.get("total_frames", 0)}\n')
        dd = p4.get('direction_distribution', {})
        if dd:
            f.write('  directions:\n')
            for d, count in dd.items():
                f.write(f'    {d}: {count}\n')
        cd4 = p4.get('confidence_distribution', {})
        if cd4:
            f.write('  confidence:\n')
            for c, count in cd4.items():
                f.write(f'    {_safe_yaml_str(str(c))}: {count}\n')

        # Timings
        timings = report.get('timings', {})
        f.write('\ntimings:\n')
        for phase, t in sorted(timings.items()):
            f.write(f'  {phase}: {t}s\n')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run figma-prepare benchmark')
    parser.add_argument('fixtures', nargs='*', help='Fixture files (XML or JSON)')
    parser.add_argument('--all', action='store_true', help='Run on all fixtures in data/')
    parser.add_argument('--results-dir', default=RESULTS_DIR, help='Output directory for results')
    args = parser.parse_args()

    results_dir = args.results_dir

    fixture_paths = []
    if args.all:
        if os.path.isdir(DATA_DIR):
            for fname in sorted(os.listdir(DATA_DIR)):
                if fname.endswith(('.xml', '.json')):
                    fixture_paths.append(os.path.join(DATA_DIR, fname))
        if not fixture_paths:
            print(f"No fixtures found in {DATA_DIR}/")
            print("Place .xml or .json fixture files in the data/ directory.")
            sys.exit(1)
    elif args.fixtures:
        fixture_paths = args.fixtures
    else:
        # Check for fixtures in data/ directory
        if os.path.isdir(DATA_DIR):
            for fname in sorted(os.listdir(DATA_DIR)):
                if fname.endswith(('.xml', '.json')):
                    fixture_paths.append(os.path.join(DATA_DIR, fname))

        if not fixture_paths:
            parser.print_help()
            print(f"\nNo fixtures provided. Place .xml or .json files in {DATA_DIR}/")
            sys.exit(1)

    all_reports = []
    for fixture_path in fixture_paths:
        if not os.path.exists(fixture_path):
            print(f"WARNING: Fixture not found: {fixture_path}")
            continue
        report = generate_report(fixture_path, results_dir)
        all_reports.append(report)

    # Print comparison summary if multiple fixtures
    if len(all_reports) > 1:
        print(f"\n{'='*70}")
        print("  COMPARISON SUMMARY")
        print(f"{'='*70}")
        header = f"  {'Fixture':<30} {'Score':>6} {'Grade':>6} {'Nodes':>7} {'Unnamed%':>9} {'Groups':>7} {'Renames':>8} {'AL':>5}"
        print(header)
        print(f"  {'-'*len(header.strip())}")
        for r in all_reports:
            p1 = r.get('phases', {}).get('phase1', {})
            p2 = r.get('phases', {}).get('phase2_stage_a', {})
            p3 = r.get('phases', {}).get('phase3', {})
            p4 = r.get('phases', {}).get('phase4', {})
            m = p1.get('metrics', {})
            name = r['fixture'][:28]
            print(f"  {name:<30} {p1.get('score', 0):>6} {p1.get('grade', '?'):>6} "
                  f"{m.get('total_nodes', 0):>7} {m.get('unnamed_rate_pct', 0):>8}% "
                  f"{p2.get('total_candidates', 0):>7} {p3.get('total_renames', 0):>8} "
                  f"{p4.get('total_frames', 0):>5}")

    print(f"\nBenchmark complete. {len(all_reports)} fixture(s) processed.")


if __name__ == '__main__':
    main()
