import React from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";

const EXAMPLES = [
  "What is the total market value across all portfolio positions?",
  "What are the top 3 customer segments by total account balance?",
  "How many trades were executed in the last 3 months with status EXECUTED?",
  "What is our risk exposure to the Technology sector for institutional accounts?",
  "Show the average VaR(95) and Sharpe ratio across all accounts.",
  "Which sectors have the highest unrealized P&L in portfolio positions?",
];

export default function ExampleQueries({ onSelect }) {
  return (
    <Container header={<Header variant="h3">Example Queries</Header>}>
      <SpaceBetween size="xs">
        {EXAMPLES.map((q, i) => (
          <Button
            key={i}
            variant="inline-link"
            onClick={() => onSelect(q)}
          >
            {q}
          </Button>
        ))}
      </SpaceBetween>
    </Container>
  );
}
