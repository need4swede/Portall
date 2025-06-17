# <a href="https://github.com/need4swede/portall/releases/tag/v2.0.3" target="_blank">v2.0.3</a>
## Added:
### Portainer SSL
Added 'Verify SSL' toggle for portainer

### Docker Socket Permissions
Permissions are now handled automatically

### Host IP Decleration
Set your host (via env variable) to override local IP declarations (ie, 127.0.0.1)

## Changed:
### Portainer Naming
Changed how portainer IP tables are named on import

### Caddyfile Imports
Added additional syntax support for Caddyfile imports

# <a href="https://github.com/need4swede/portall/releases/tag/v2.0.2" target="_blank">v2.0.2</a>
## Fixed:
### Port Scanning
Fixed an issue where Port Scanning wasn't available

### Startup Script
Fixed issue with startup script not initializing properly

### Migration Logic
Fixed issue where migrations weren't completing successfully

# <a href="https://github.com/need4swede/portall/releases/tag/v2.0.1" target="_blank">v2.0.1</a>
## Fixed:
### Database Permission Issue
Fixed an issue where Portall was unable to write to the databsase

# <a href="https://github.com/need4swede/portall/releases/tag/v2.0.0" target="_blank">v2.0.0</a>
## Added:
### Docker Integration
- Auto-detection of Docker containers and port mappings
- Configurable Docker connection settings
- Socket proxy architecture using 11notes/socket-proxy:stable
- Read-only Docker API access with network isolation

### Portainer Integration
- Auto-detection of Portainer containers and port mappings

### Komodo Integration
- Auto-detection of Komodo containers and port mappings

### Port Scanning
- Ability to scan IP addresses for open ports
- Background scanning with configurable intervals

## Changed:
### UI Overhaul
- Brand new interface, with support for both dark and light mode
- Smoother animations and greater emphasis on communication
- Improve mobile responsive layout

### Improved JSON data ingestion
- JSON exports now contain more information about your Portall instance
- JSON imports from a v2.x export now restores your entire instance
- CAUTION: This data now includes API keys if using Docker integrations!

### Security
- Added dedicated portall-network for service isolation
- Implemented read-only containers with tmpfs mounts
- Container hardening with capability restrictions

## Fixed:
### Inability to move IP tables
Fixed a bug where moving tables around would cause crashes
### Moved Ports not saving their new IP
Fixed a bug where certain Ports would return to their old IP address on refresh

# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.8" target="_blank">v1.0.8</a>
## Changed:
### Overhauled Docker-Compose Imports
Complete rewrite of how docker-compose data is imported to make the import logic more versititle.

# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.7" target="_blank">v1.0.7</a>
## Added:
### Sorting
You can now quickly sort your ports by port number or by protocol type. Manually sorting your ports via drag-and-drop is still supported.
### Database Migration
Portall will now automatically migrate your database on version changes.
### <a href="https://github.com/need4swede/Portall/issues/20" target="_blank">Docker-Compose Anchors</a>
Added support for anchors in docker-compose imports. Port descriptions are still pulled from the image name.
## Changed:
### Restructured AJAX Calls
Renamed and restructured all AJAX calls.
### Skip Existing Ports on Import
Imports now skip adding ports that already exists in your database.
## Fixed:
### Missing Nicknames
Fixed an issue where nicknames wouldn't get properly parsed when adding or importing ports.
### Moving Ports Creates Host
Fixed a bug where moving a port from one host to another would register a new IP address.
### New Ports Missing Order
Fixed a bug where newly added ports wouldn't have their order updated unless explicitly moved.
### Protocol Detection When Adding Ports
Fixed a bug where port protocols wouldn't get caught for conflicts due to case-sensitivity.

# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.6" target="_blank">v1.0.6</a>
## Added:
### Port Protocols
Portall now supports setting different protocols for ports (TCP/UDP).

You can choose protocols when generating new ports (default is TCP), when creating new ones, and when editing existing ones. Two identical port numbers can both be registered to a single IP if they have different protocols. If you try to add an entry that already has a matching port and protocol, it will trigger the Port Conflict Resolver.

If you add ports from an import, such as a Caddyfile or Docker-Compose, that doesn't explicitly state what protocols are being used, it will default to TCP.
### Loading Animation
Certain actions, like port conflict resolutions and moving IP panels, now trigger a loading animation that prevents further action until the changes have registered.
## Changed:
### Database
**Breaking Changes!** Database changes required for new port protocol feature.
### Docker-Compose Imports
Now supports `/tcp` and `/udp` properties to differentiate between the two protocols.
## Fixed:
### <a href="https://github.com/need4swede/Portall/issues/10" target="_blank">Settings Reset</a>
Fixed an issue where certain settings would reset if you made changes in the settings.

# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.5" target="_blank">v1.0.5</a>
## Added:
### <a href="https://github.com/need4swede/Portall/issues/7" target="_blank">Data Export</a>
You can now export your entries to a JSON file.
## Changed:
### JSON Import
Updated the format of JSON imports to match the new export,
## Fixed:
### <a href="https://github.com/need4swede/Portall/issues/14" target="_blank">Newly Added Port Order</a>
Fixed an issue where newly added ports would get placed near the beggining of the stack. Now they get appended to the end,

# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.4" target="_blank">v1.0.4</a>
## Added:
### Port Conflict Resolution
In the event of moving a port to a different IP panel where the port is already registered, a new conflict resolution modal will present users with three options to choose from:

- Change the number of the migrating port
- Change the number of the existing port
- Cancel the action

This will prevent port conflicts when moving between hosts and give users an intuative way to migrate their ports and services over between IP's.
## Changed:
### Codebase Cleanup
Refactored files and much of the code to make the applicaiton more modular.
## Fixed:
### Port Positioning
Fixed a bug that would reset a port's position within an IP panel.
### Can't edit last port
Fixed a bug that prevented users from editing the only remaining port in an IP panel.

# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.3" target="_blank">v1.0.3</a>
## Changed:
### Unique Port Numbers
Port numbers now have to be unique within an IP panel. You cannot add a service using an already registered port number, nor can you change a port to a number that is already registered.
## Fixed:
### <a href="https://github.com/need4swede/Portall/issues/8" target="_blank">Port ID Bug</a>
Fixed an issue where the ID of a port wasn't being read correctly.

<hr>
# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.2" target="_blank">v1.0.2</a>
## Changed:
**Breaking Change!** - Altered database structure to handle new ordering logic.
## Fixed:
### <a href="https://github.com/need4swede/Portall/issues/2" target="_blank">Port Order Bug</a>
Fixed an issue where re-arranged ports would not have their order saved.

<hr>
# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.1" target="_blank">v1.0.1</a>
## Added:
### Changelog section
Track changes between app versions. Found under `Settings > About`
### Planned Features section
See what is planned for future releases. Found under `Settings > About`
### linux/arm64 support
Added support for linux/arm64, which was absent in the initial release.
## Fixed:
### Docker-Compose import bug
Fixed bug that wouldn't detect ports for certain Docker-Compose imports

<hr>
# <a href="https://github.com/need4swede/portall/releases/tag/v1.0.0" target="_blank">v1.0.0</a>
### Initial Release
Initial public release of Portal
