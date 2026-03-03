
// Vite Development Mode
// WordPress初回起動後、wp-config.phpの "stop editing" の直前に以下を追加
define('VITE_DEV_MODE', getenv_docker('VITE_DEV', '0') === '1');
