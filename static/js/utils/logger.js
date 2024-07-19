// static/js/utils/logger.js

/**
 * Logs configuration information for enabled plugins.
 *
 * @param {string} name - The name of the plugin
 * @param {...Object} args - Additional key-value pairs of plugin configuration
 */
export function logPluginsConfig(name, ...args) {
    if (!name) {
        console.error("Plugin name is required for logging");
        return;
    }

    let configObject = { name };

    args.forEach(arg => {
        if (typeof arg === 'object' && arg !== null) {
            Object.assign(configObject, arg);
        }
    });

    console.log(`Loaded Plugin: ${JSON.stringify(configObject)}`);
}