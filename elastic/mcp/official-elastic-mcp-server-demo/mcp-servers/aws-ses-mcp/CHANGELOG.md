# Changelog

All notable changes to the MCP Send Email project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Advanced email recipient management:
  - CC support for carbon copy recipients
  - BCC support for blind carbon copy recipients
- Enhanced logging system:
  - Full request/response logging for improved debugging
  - Detailed error tracking and reporting
- Documentation improvements:
  - Comprehensive "Features" section in README
  - Detailed setup instructions for both Cursor and Claude Desktop
  - Usage examples for CC/BCC in email.md
  - Troubleshooting guide
- Email validation and error handling
- Support for multiple reply-to addresses

### Fixed
- Sender email validation and handling with AWS SES
- Type definitions for email request object
- Error handling for invalid email formats
- Documentation links and examples

### Changed
- Enhanced console logging system:
  - More detailed error messages
  - Better formatting for log outputs
  - Added timestamp to log entries
- Documentation updates:
  - Restructured README for better clarity
  - Updated AWS SES setup requirements
  - Added emoji icons for better visual organization
  - Improved code examples and configuration guides

### Security
- Added input validation for email addresses
- Improved handling of AWS credentials
- Added checks for email sending permissions

## [1.0.0] - 2025-02-24

### Added
- Initial release with core features:
  - Basic email sending functionality via AWS SES
  - HTML email support with plain text fallback
  - Email scheduling capability
  - Reply-to addressing support
  - Basic error handling
  - Simple logging system

### Security
- Basic AWS credential management
- Email address validation

[Unreleased]: https://github.com/yourusername/aws-ses/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/aws-ses/releases/tag/v1.0.0 