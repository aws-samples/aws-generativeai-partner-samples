import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import AWS from "aws-sdk";
import minimist from "minimist";

// Parse command line arguments
const argv = minimist(process.argv.slice(2));

// Get AWS credentials from environment variables or command line arguments
const awsAccessKeyId = argv["aws-access-key-id"] || process.env.AWS_ACCESS_KEY_ID;
const awsSecretAccessKey = argv["aws-secret-access-key"] || process.env.AWS_SECRET_ACCESS_KEY;
const awsRegion = argv["aws-region"] || process.env.AWS_REGION || "us-east-1";

// Get sender email address from command line argument or fall back to environment variable
const senderEmailAddress = argv.sender || process.env.SENDER_EMAIL_ADDRESS;

// Get reply to email addresses from command line argument or fall back to environment variable
let replierEmailAddresses: string[] = [];

if (Array.isArray(argv["reply-to"])) {
  replierEmailAddresses = argv["reply-to"];
} else if (typeof argv["reply-to"] === "string") {
  replierEmailAddresses = [argv["reply-to"]];
} 

if (!awsAccessKeyId || !awsSecretAccessKey) {
  console.error(
    "AWS credentials not provided. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or use --aws-access-key-id and --aws-secret-access-key arguments"
  );
  process.exit(1);
}

// Initialize AWS SES client
AWS.config.update({
  accessKeyId: awsAccessKeyId,
  secretAccessKey: awsSecretAccessKey,
  region: awsRegion
});

const ses = new AWS.SES();

// Create server instance
const server = new McpServer({
  name: "email-sending-service",
  version: "1.0.0",
});

server.tool(
  "send-email",
  "Send an email using AWS SES",
  {
    to: z.string().email().describe("Recipient email address"),
    subject: z.string().describe("Email subject line"),
    text: z.string().describe("Plain text email content"),
    html: z
      .string()
      .optional()
      .describe(
        "HTML email content. When provided, the plain text argument MUST be provided as well."
      ),
    cc: z
      .string()
      .email()
      .array()
      .optional()
      .describe("Optional array of CC email addresses. You MUST ask the user for this parameter. Under no circumstance provide it yourself"),
    bcc: z
      .string()
      .email()
      .array()
      .optional()
      .describe("Optional array of BCC email addresses. You MUST ask the user for this parameter. Under no circumstance provide it yourself"),
    // Note: Removed scheduledAt as AWS SES doesn't support scheduling directly
    // If sender email address is not provided, the tool requires it as an argument
    ...(!senderEmailAddress
      ? {
          from: z
            .string()
            .email()
            .nonempty()
            .describe(
              "Sender email address. You MUST ask the user for this parameter. Under no circumstance provide it yourself"
            ),
        }
      : {}),
    ...(replierEmailAddresses.length === 0
      ? {
          replyTo: z
            .string()
            .email()
            .array()
            .optional()
            .describe(
              "Optional email addresses for the email readers to reply to. You MUST ask the user for this parameter. Under no circumstance provide it yourself"
            ),
        }
      : {}),
  },
  async ({ from, to, subject, text, html, replyTo, cc, bcc }) => {
    const fromEmailAddress = from ?? senderEmailAddress;
    const replyToEmailAddresses = replyTo ?? replierEmailAddresses;

    // Type check on from, since "from" is optionally included in the arguments schema
    if (typeof fromEmailAddress !== "string") {
      throw new Error("from argument must be provided.");
    }

    // Similar type check for "reply-to" email addresses.
    if (
      typeof replyToEmailAddresses !== "string" &&
      !Array.isArray(replyToEmailAddresses)
    ) {
      throw new Error("replyTo argument must be provided.");
    }

    console.error(`Debug - Sending email with from: ${fromEmailAddress}`);
    
    // Prepare the email parameters for AWS SES
    const emailParams = {
      Source: fromEmailAddress,
      Destination: {
        ToAddresses: [to],
        ...(cc && { CcAddresses: cc }),
        ...(bcc && { BccAddresses: bcc }),
      },
      Message: {
        Subject: {
          Data: subject,
          Charset: "UTF-8",
        },
        Body: {
          Text: {
            Data: text,
            Charset: "UTF-8",
          },
          ...(html && {
            Html: {
              Data: html,
              Charset: "UTF-8",
            },
          }),
        },
      },
      ReplyToAddresses: Array.isArray(replyToEmailAddresses) 
        ? replyToEmailAddresses 
        : [replyToEmailAddresses],
    };
    
    console.error(`Email request: ${JSON.stringify(emailParams)}`);

    try {
      const response = await ses.sendEmail(emailParams).promise();

      return {
        content: [
          {
            type: "text",
            text: `Email sent successfully! MessageId: ${response.MessageId}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(
        `Email failed to send: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Email sending service MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
