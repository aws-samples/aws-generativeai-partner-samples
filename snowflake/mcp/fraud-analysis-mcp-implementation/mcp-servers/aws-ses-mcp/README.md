# aws-ses-mcp 📧

[![smithery badge](https://smithery.ai/badge/@omd01/aws-ses-mcp)](https://smithery.ai/server/@omd01/aws-ses-mcp)


This is a simple MCP server that sends emails using AWS SES (Simple Email Service). Perfect for integrating with Cursor or Claude Desktop to compose and send emails directly without copy-pasting. The service supports both plain text and HTML emails with advanced features like CC, BCC, and reply-to functionality.

## Features ✨

- Send plain text and HTML emails
- Support for CC and BCC recipients
- Configurable reply-to addresses
- Customizable sender email (requires AWS SES verification)
- Full request/response logging for debugging
- Email scheduling capability

## Prerequisites 📋

Before you begin, ensure you have:

1. AWS SES account set up and configured
2. Verified email domain or individual email addresses in AWS SES
3. AWS credentials (Access Key ID and Secret Access Key) with SES permissions
4. Node.js installed on your system

## Installation 🚀

### Installing via Smithery

To install aws-ses-mcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@omd01/aws-ses-mcp):

```bash
npx -y @smithery/cli install @omd01/aws-ses-mcp --client claude
```

### Manual Installation
1. Clone this repository:
```bash
git clone https://github.com/omd01/aws-ses-mcp.git
cd aws-ses-mcp
```

2. Install dependencies:
```bash
npm install
```

3. Build the project:
```bash
npm run build
```

## Configuration ⚙️

### Example Email Format (email.md)
```json
{
  "to": "example@gmail.com",
  "subject": "Test!",
  "text": "This is a test email.",
  "cc": ["cc-recipient@example.com"],
  "bcc": ["bcc-recipient@example.com"]
}
```

## Setup Instructions 🔧

### For Cursor

1. Go to Cursor Settings -> MCP -> Add new MCP server

2. Configure the server with these settings:
   - Name: `aws-ses-mcp` (or your preferred name)
   - Type: `command`
   - Command: 
   ```bash
   node ABSOLUTE_PATH_TO_MCP_SERVER/build/index.js \
   --aws-access-key-id=YOUR_AWS_ACCESS_KEY_ID \
   --aws-secret-access-key=YOUR_AWS_SECRET_ACCESS_KEY \
   --aws-region=YOUR_AWS_REGION \
   --sender=YOUR_SENDER_EMAIL \
   --reply-to=REPLY_TO_EMAIL
   ```

### For Claude Desktop

Add the following configuration to your MCP config:

```json
{
  "mcpServers": {
    "aws-ses-mcp": {
      "command": "node",
      "args": ["ABSOLUTE_PATH_TO_MCP_SERVER/build/index.js"],
      "env": {
        "AWS_ACCESS_KEY_ID": "YOUR_AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY": "YOUR_AWS_SECRET_ACCESS_KEY",
        "AWS_REGION": "YOUR_AWS_REGION",
        "SENDER_EMAIL_ADDRESS": "YOUR_SENDER_EMAIL",
        "REPLY_TO_EMAIL_ADDRESSES": "REPLY_TO_EMAILS_COMMA_SEPARATED"
      }
    }
  }
}
```

## Usage 📝

1. Create or edit `email.md` with your email content
2. In Cursor:
   - Open the email.md file
   - Select the content
   - Press cmd+l (or ctrl+l)
   - Tell Cursor to "send this as an email"
   - Ensure Cursor chat is in Agent mode

## Development 👩‍💻

```bash
npm install    # Install dependencies
npm run build  # Build the project
```

## Troubleshooting 🔍

- Check the console logs for detailed request/response information
- Verify your AWS credentials and permissions
- Ensure your sender email is verified in AWS SES
- Review the AWS SES console for any bounces or complaints

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that is short and to the point. It lets people do anything they want with your code as long as they provide attribution back to you and don't hold you liable.
