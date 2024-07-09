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