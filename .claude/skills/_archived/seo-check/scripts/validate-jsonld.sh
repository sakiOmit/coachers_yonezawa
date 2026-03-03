#!/bin/bash
# JSON-LD Validation Script
# Usage: bash validate-jsonld.sh {file}
# Exit 0: PASS, Exit 1: FAIL

set -euo pipefail

FILE="$1"
ERRORS=0

if [ ! -f "$FILE" ]; then
  echo "❌ File not found: $FILE"
  exit 1
fi

echo "🔍 Validating JSON-LD: $FILE"

# Extract JSON-LD blocks
JSONLD_BLOCKS=$(grep -Pzo '(?s)<script type="application/ld\+json">(.*?)</script>' "$FILE" | tr '\0' '\n' || echo "")

if [ -z "$JSONLD_BLOCKS" ]; then
  echo "⚠️  No JSON-LD found"
  exit 0  # Not an error, just no structured data
fi

# Extract JSON content (remove script tags)
JSON_CONTENT=$(echo "$JSONLD_BLOCKS" | sed -n 's/<script type="application\/ld+json">\(.*\)<\/script>/\1/p')

if [ -z "$JSON_CONTENT" ]; then
  echo "⚠️  JSON-LD block empty"
  exit 0
fi

# Validate JSON syntax
if ! echo "$JSON_CONTENT" | jq empty 2>/dev/null; then
  echo "❌ Invalid JSON syntax"
  ERRORS=$((ERRORS + 1))
fi

# Extract @type
TYPE=$(echo "$JSON_CONTENT" | jq -r '."@type"' 2>/dev/null || echo "")

if [ -z "$TYPE" ]; then
  echo "❌ Missing @type property"
  ERRORS=$((ERRORS + 1))
  exit 1
fi

echo "✓ @type: $TYPE"

# Validate based on @type
case "$TYPE" in
  "JobPosting")
    echo "📋 Validating JobPosting schema..."

    # Required properties
    TITLE=$(echo "$JSON_CONTENT" | jq -r '.title' 2>/dev/null || echo "null")
    DESCRIPTION=$(echo "$JSON_CONTENT" | jq -r '.description' 2>/dev/null || echo "null")
    DATE_POSTED=$(echo "$JSON_CONTENT" | jq -r '.datePosted' 2>/dev/null || echo "null")
    HIRING_ORG=$(echo "$JSON_CONTENT" | jq -r '.hiringOrganization.name' 2>/dev/null || echo "null")
    JOB_LOCATION=$(echo "$JSON_CONTENT" | jq -r '.jobLocation.address' 2>/dev/null || echo "null")

    if [ "$TITLE" = "null" ]; then
      echo "❌ Missing required property: title"
      ERRORS=$((ERRORS + 1))
    else
      echo "✓ title: $TITLE"
    fi

    if [ "$DESCRIPTION" = "null" ]; then
      echo "❌ Missing required property: description"
      ERRORS=$((ERRORS + 1))
    else
      DESC_LENGTH=${#DESCRIPTION}
      if [ "$DESC_LENGTH" -lt 50 ]; then
        echo "⚠️  description too short: $DESC_LENGTH chars (min: 50)"
      else
        echo "✓ description: $DESC_LENGTH chars"
      fi
    fi

    if [ "$DATE_POSTED" = "null" ]; then
      echo "❌ Missing required property: datePosted"
      ERRORS=$((ERRORS + 1))
    else
      # Validate ISO 8601 format (basic check)
      if echo "$DATE_POSTED" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'; then
        echo "✓ datePosted: $DATE_POSTED"
      else
        echo "❌ Invalid datePosted format: $DATE_POSTED (expected ISO 8601)"
        ERRORS=$((ERRORS + 1))
      fi
    fi

    if [ "$HIRING_ORG" = "null" ]; then
      echo "❌ Missing required property: hiringOrganization.name"
      ERRORS=$((ERRORS + 1))
    else
      echo "✓ hiringOrganization.name: $HIRING_ORG"
    fi

    if [ "$JOB_LOCATION" = "null" ]; then
      echo "❌ Missing required property: jobLocation.address"
      ERRORS=$((ERRORS + 1))
    else
      echo "✓ jobLocation.address: present"
    fi
    ;;

  "Organization")
    echo "🏢 Validating Organization schema..."

    NAME=$(echo "$JSON_CONTENT" | jq -r '.name' 2>/dev/null || echo "null")
    URL=$(echo "$JSON_CONTENT" | jq -r '.url' 2>/dev/null || echo "null")
    LOGO=$(echo "$JSON_CONTENT" | jq -r '.logo' 2>/dev/null || echo "null")

    if [ "$NAME" = "null" ]; then
      echo "❌ Missing required property: name"
      ERRORS=$((ERRORS + 1))
    else
      echo "✓ name: $NAME"
    fi

    if [ "$URL" = "null" ]; then
      echo "❌ Missing required property: url"
      ERRORS=$((ERRORS + 1))
    else
      echo "✓ url: $URL"
    fi

    if [ "$LOGO" = "null" ]; then
      echo "⚠️  Recommended property missing: logo"
    else
      echo "✓ logo: present"
    fi
    ;;

  *)
    echo "⚠️  Unknown @type: $TYPE (skipping validation)"
    ;;
esac

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "❌ Validation failed: $ERRORS errors"
  exit 1
fi

echo ""
echo "✅ JSON-LD validation passed"
exit 0
