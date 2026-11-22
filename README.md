# SandScope
# SandScope — Infrastructure & Environment

## Person 1: Infrastructure and Environment Preparation

### Overview
This component prepares the isolated Windows sandbox environment used by SandScope for controlled security analysis.

### Environment
- Virtualization: VMware Workstation Pro
- Guest OS: Windows 10
- Python: 3.13
- Network: VMware LAN Segment (`sandbox lan`)
- Shared folders: Disabled
- Clipboard sharing: Disabled
- Drag-and-drop: Disabled

### Tools
- Procmon — Process and system activity monitoring
- capa — Capability analysis
- Sysmon — Telemetry integration (coordinated with Person 2)

### Components
- Environment collector
- Environment findings generator
- Baseline validator
- Host-side VMware controller
- Guest-side validation runner
- Controlled execution runner
- SHA-256 approval verification
- Harmless test simulator

### Directory Structure
See `person1-infrastructure/`.

### Safety
- Analysis VM must remain isolated.
- Do not use Bridged networking.
- Do not run unapproved samples.
- Only use instructor-approved or harmless test simulators.
- Restore a clean baseline when required.
- Never upload credentials or unredacted VM configuration.

### Current Status
Infrastructure and environment preparation completed.

Controlled execution and telemetry integration require final verification and coordination with other team members.

### Recovery
The VM has a snapshot named `SandScope-complete-baseline`.

### Team
SandScope Cyber Security Project.
