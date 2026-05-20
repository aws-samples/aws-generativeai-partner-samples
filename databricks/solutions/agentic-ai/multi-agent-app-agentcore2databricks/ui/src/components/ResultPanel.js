import React from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Box from "@cloudscape-design/components/box";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const markdownStyles = `
  .result-markdown h2 {
    font-size: 1.25rem;
    font-weight: 700;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #e9ebed;
    color: #16191f;
  }
  .result-markdown h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
    color: #16191f;
  }
  .result-markdown p {
    margin-bottom: 0.75rem;
    line-height: 1.7;
    color: #16191f;
  }
  .result-markdown ul, .result-markdown ol {
    margin-bottom: 0.75rem;
    padding-left: 1.5rem;
  }
  .result-markdown li {
    margin-bottom: 0.4rem;
    line-height: 1.6;
  }
  .result-markdown strong {
    color: #0972d3;
  }
  .result-markdown table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 1rem 0;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
    border: 1px solid #e9ebed;
  }
  .result-markdown thead {
    background: linear-gradient(135deg, #232f3e 0%, #37475a 100%);
  }
  .result-markdown thead th {
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #ffffff;
    border-bottom: 2px solid #0972d3;
  }
  .result-markdown tbody tr {
    transition: background-color 0.15s ease;
  }
  .result-markdown tbody tr:nth-child(even) {
    background-color: #f9fafb;
  }
  .result-markdown tbody tr:hover {
    background-color: #f1f5f9;
  }
  .result-markdown tbody td {
    padding: 10px 16px;
    font-size: 0.9rem;
    color: #16191f;
    border-bottom: 1px solid #e9ebed;
    vertical-align: top;
  }
  .result-markdown tbody tr:last-child td {
    border-bottom: none;
  }
  .result-markdown code {
    background-color: #f1f3f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85rem;
    color: #d63384;
  }
  .result-markdown pre {
    background-color: #232f3e;
    color: #f8f9fa;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1rem 0;
  }
  .result-markdown pre code {
    background: none;
    color: inherit;
    padding: 0;
  }
  .result-markdown blockquote {
    border-left: 4px solid #0972d3;
    margin: 1rem 0;
    padding: 0.75rem 1rem;
    background-color: #f0f7ff;
    border-radius: 0 6px 6px 0;
    color: #16191f;
  }
  .result-markdown hr {
    border: none;
    border-top: 1px solid #e9ebed;
    margin: 1.5rem 0;
  }
`;

export default function ResultPanel({ answer }) {
  if (!answer) {
    return (
      <Container header={<Header variant="h3">Final Answer</Header>}>
        <Box color="text-body-secondary" textAlign="center" padding="l">
          No result yet. Run an analysis to see the response.
        </Box>
      </Container>
    );
  }

  return (
    <Container header={<Header variant="h3">Synthesized Analysis</Header>}>
      <style>{markdownStyles}</style>
      <div className="result-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
      </div>
    </Container>
  );
}
