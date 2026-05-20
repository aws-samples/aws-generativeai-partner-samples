import React, { useState, useRef, useCallback } from "react";
import AppLayout from "@cloudscape-design/components/app-layout";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Container from "@cloudscape-design/components/container";
import FormField from "@cloudscape-design/components/form-field";
import Textarea from "@cloudscape-design/components/textarea";
import Button from "@cloudscape-design/components/button";
import RadioGroup from "@cloudscape-design/components/radio-group";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Box from "@cloudscape-design/components/box";
import Badge from "@cloudscape-design/components/badge";
import Alert from "@cloudscape-design/components/alert";
import Tabs from "@cloudscape-design/components/tabs";
import AgentFlowVisualization from "./components/AgentFlowVisualization";
import ResultPanel from "./components/ResultPanel";
import ExampleQueries from "./components/ExampleQueries";

const WS_URL = "ws://localhost:8000/ws/query";

export default function App() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("raw");
  const [events, setEvents] = useState([]);
  const [answer, setAnswer] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef(null);

  const handleSubmit = useCallback(() => {
    if (!question.trim() || isRunning) return;

    setEvents([]);
    setAnswer("");
    setError("");
    setIsRunning(true);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ question: question.trim(), mode }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);

      if (data.type === "complete") {
        setAnswer(data.answer || "");
        setIsRunning(false);
        ws.close();
      } else if (data.type === "error") {
        setError(data.message || "Unknown error");
        setIsRunning(false);
        ws.close();
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection failed. Is the backend running?");
      setIsRunning(false);
    };

    ws.onclose = () => {
      setIsRunning(false);
    };
  }, [question, mode, isRunning]);

  const handleExampleClick = (q) => {
    setQuestion(q);
  };

  return (
    <AppLayout
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              description="Hybrid multi-agent system: Amazon Bedrock AgentCore + Databricks Agent Framework"
            >
              Multi-Agent Financial Analyst
            </Header>
          }
        >
          <SpaceBetween size="l">
            {/* Query Input */}
            <Container
              header={<Header variant="h2">Ask a Question</Header>}
            >
              <SpaceBetween size="m">
                <FormField label="Financial Analysis Query">
                  <Textarea
                    value={question}
                    onChange={({ detail }) => setQuestion(detail.value)}
                    placeholder="Enter your financial analysis question..."
                    rows={3}
                  />
                </FormField>

                <ColumnLayout columns={2}>
                  <FormField label="Agent Mode">
                    <RadioGroup
                      value={mode}
                      onChange={({ detail }) => setMode(detail.value)}
                      items={[
                        {
                          value: "raw",
                          label: "Standard Agents",
                          description: "Manual orchestration: Supervisor → Data Analyst → Validator → Synthesizer",
                        },
                        {
                          value: "strands",
                          label: "Strands SDK Agents",
                          description: "Autonomous: Strands Agent decides tool calling order dynamically",
                        },
                      ]}
                    />
                  </FormField>

                  <Box>
                    <SpaceBetween size="xs">
                      <Box variant="awsui-key-label">Architecture</Box>
                      <Box>
                        <Badge color="blue">Bedrock Claude</Badge>{" "}
                        <Badge color="green">AgentCore Gateway</Badge>{" "}
                        <Badge color="grey">Databricks MCP</Badge>
                      </Box>
                      <Box variant="small" color="text-body-secondary">
                        Supervisor + Synthesizer on AWS | Data Analyst + Validator on Databricks
                      </Box>
                    </SpaceBetween>
                  </Box>
                </ColumnLayout>

                <Button
                  variant="primary"
                  onClick={handleSubmit}
                  loading={isRunning}
                  disabled={!question.trim()}
                >
                  {isRunning ? "Analyzing..." : "Run Analysis"}
                </Button>
              </SpaceBetween>
            </Container>

            {/* Example Queries */}
            <ExampleQueries onSelect={handleExampleClick} />

            {/* Error */}
            {error && <Alert type="error" header="Error">{error}</Alert>}

            {/* Architecture Diagram + Agent Flow Visualization + Results (shown after Run Analysis) */}
            {events.length > 0 && (
              <Container
                header={<Header variant="h2">Architecture</Header>}
              >
                <Box textAlign="center">
                  <img
                    src="/architecture-diagram.png"
                    alt="Multi-Agent Architecture Diagram"
                    style={{ maxWidth: "100%", height: "auto" }}
                  />
                </Box>
              </Container>
            )}

            {events.length > 0 && (
              <Tabs
                tabs={[
                  {
                    id: "flow",
                    label: "Agent Flow",
                    content: <AgentFlowVisualization events={events} isRunning={isRunning} />,
                  },
                  {
                    id: "result",
                    label: "Final Answer",
                    content: <ResultPanel answer={answer} />,
                    disabled: !answer,
                  },
                ]}
              />
            )}
          </SpaceBetween>
        </ContentLayout>
      }
      navigationHide
      toolsHide
    />
  );
}
