# Changelog - Livewire Mapper

## [v5.3.0] - 2026-02-18
### Fixed
- **Network Master Display**: Fixed a UI bug where the "Network Master" label remained on "Searching" even after the master node was identified.
- **Red Alert Logging**: Restored and improved red-colored log entries to specifically highlight "Real" conflicts and hardware connection refusals.
- **UI Refresh**: Forced immediate UI updates upon successful node queries to improve real-time feel.

## [v5.2.9] - 2026-02-18
### Added
- **Smart Conflict Logic**: Implemented a "Backfeed Filter" that prevents intentional "To:" sources from triggering false positive conflict alerts.
- **Safe Path Escaping**: Added support for file paths and names containing single quotes for the VLC recording engine.

## [v5.2.8] - 2026-02-18
### Added
- **Export to CSV**: Added a dedicated button to generate timestamped snapshots of the entire network map.
- **Disk Space Protection**: Integrated a real-time disk usage monitor and a 500MB safety cutoff for recordings.
- **Custom Storage Paths**: Added the ability for users to select a custom directory for audio captures.
