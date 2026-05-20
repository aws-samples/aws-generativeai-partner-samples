import React, { useMemo, useState } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Box from "@cloudscape-design/components/box";
import Spinner from "@cloudscape-design/components/spinner";
import SpaceBetween from "@cloudscape-design/components/space-between";
import ColumnLayout from "@cloudscape-design/components/column-layout";

function AwsLogo({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <path d="M18.7 34.7c0 .8.1 1.5.3 2 .2.5.5 1.1.9 1.7.1.2.2.4.2.5 0 .2-.1.4-.4.6l-1.2.8c-.2.1-.3.2-.5.2-.2 0-.4-.1-.6-.3-.3-.3-.5-.6-.7-1-.2-.3-.4-.7-.6-1.2-1.5 1.8-3.4 2.7-5.7 2.7-1.6 0-2.9-.5-3.8-1.4-.9-1-1.4-2.2-1.4-3.8 0-1.7.6-3 1.8-4.1 1.2-1 2.8-1.5 4.8-1.5.7 0 1.4.1 2.1.2.7.1 1.5.3 2.3.5v-1.4c0-1.5-.3-2.5-1-3.2-.6-.7-1.7-1-3.2-1-.7 0-1.4.1-2.1.3-.7.2-1.5.5-2.1.8-.3.2-.5.2-.7.3-.2 0-.3.1-.4.1-.3 0-.5-.2-.5-.7v-1c0-.4.1-.6.2-.8.1-.2.4-.3.7-.5.7-.4 1.6-.7 2.5-.9 1-.2 2-.4 3.1-.4 2.3 0 4 .5 5.1 1.6 1.1 1.1 1.6 2.7 1.6 4.9v6.5h.1zM12.3 38c.7 0 1.3-.1 2-.4.7-.2 1.3-.7 1.8-1.3.3-.4.5-.8.7-1.3.1-.5.2-1.1.2-1.8v-.9c-.6-.2-1.2-.3-1.9-.4-.7-.1-1.3-.2-2-.2-1.3 0-2.2.2-2.9.8-.7.5-1 1.2-1 2.2 0 .9.2 1.6.7 2.1.5.5 1.3.8 2.2.8l.2-.6zM29 39c-.4 0-.7-.1-.8-.2-.2-.2-.3-.4-.4-.8l-4.8-15.9c-.1-.4-.2-.7-.2-.8 0-.3.2-.5.5-.5h1.9c.4 0 .7.1.8.2.2.2.3.4.4.8l3.4 13.5 3.2-13.5c.1-.4.2-.7.4-.8.2-.2.5-.2.9-.2h1.6c.4 0 .7.1.9.2.2.2.3.4.4.8l3.2 13.7 3.5-13.7c.1-.4.2-.7.4-.8.2-.2.5-.2.8-.2h1.8c.3 0 .5.2.5.5 0 .1 0 .2-.1.4 0 .1-.1.3-.2.5L42 38c-.1.4-.2.7-.4.8-.2.2-.5.2-.8.2h-1.7c-.4 0-.7-.1-.9-.2-.2-.2-.3-.4-.4-.8L35.7 25l-3.1 13c-.1.4-.2.7-.4.8-.2.2-.5.2-.9.2H29zM52.4 40.2c-1 0-2-.1-2.9-.4-1-.3-1.7-.6-2.2-1-.3-.2-.5-.4-.6-.6-.1-.2-.1-.4-.1-.6v-1c0-.5.2-.7.5-.7.1 0 .3 0 .4.1.1.1.3.2.5.3.7.3 1.4.6 2.2.8.8.2 1.5.3 2.3.3 1.2 0 2.2-.2 2.8-.7.6-.5 1-1.1 1-2 0-.6-.2-1-.5-1.4-.4-.4-1-.7-2-1l-2.8-.9c-1.4-.5-2.5-1.1-3.2-2-.7-.8-1-1.8-1-2.8 0-.8.2-1.5.5-2.2.4-.6.8-1.2 1.4-1.6.6-.5 1.3-.8 2.1-1 .8-.2 1.6-.3 2.5-.3.5 0 .9 0 1.4.1.5.1.9.2 1.3.3.4.1.8.3 1.1.4.3.2.6.3.8.5.2.1.4.3.5.5.1.2.1.4.1.7v.9c0 .5-.2.7-.5.7-.2 0-.5-.1-.8-.3-1.2-.5-2.5-.8-3.9-.8-1.1 0-2 .2-2.6.6-.6.4-.9 1-.9 1.8 0 .6.2 1.1.6 1.4.4.4 1.1.7 2.1 1l2.8.9c1.4.5 2.4 1.1 3 1.9.6.8 1 1.7 1 2.8 0 .8-.2 1.6-.5 2.2-.4.7-.8 1.2-1.5 1.7-.6.5-1.3.8-2.2 1-.9.3-1.8.4-2.7.4z" fill="#252F3E"/>
      <path d="M57.3 46.8c-7 5.2-17.2 8-26 8-12.3 0-23.3-4.5-31.7-12-.7-.6-.1-1.4.7-.9 9 5.2 20.2 8.4 31.7 8.4 7.8 0 16.3-1.6 24.2-5 1.2-.5 2.2.8 1.1 1.5z" fill="#FF9900"/>
      <path d="M60.1 43.6c-.9-1.2-5.9-.6-8.2-.3-.7.1-.8-.5-.2-1 4-2.8 10.6-2 11.4-1.1.8 1-.2 7.5-4 10.6-.6.5-1.1.2-.9-.4.8-2.1 2.8-6.7 1.9-7.8z" fill="#FF9900"/>
    </svg>
  );
}

function DatabricksLogo({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 4L4 19.6v7.2l28 15.6 28-15.6v-7.2L32 4z" fill="#FF3621"/>
      <path d="M32 4L4 19.6l28 15.6 28-15.6L32 4z" fill="#FF3621" opacity="0.85"/>
      <path d="M4 26.8v7.2l28 15.6 28-15.6v-7.2L32 42.4 4 26.8z" fill="#FF3621" opacity="0.7"/>
      <path d="M4 41.2v7.2L32 64l28-15.6v-7.2L32 56.8 4 41.2z" fill="#FF3621" opacity="0.55"/>
    </svg>
  );
}

function PlatformBadge({ platform }) {
  if (platform === "aws") {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "#f0f7ff", border: "1px solid #0972d3", borderRadius: 12, padding: "2px 8px 2px 4px", fontSize: "0.65rem", fontWeight: 600, color: "#0972d3" }}>
        <AwsLogo size={14} /> AWS
      </span>
    );
  }
  if (platform === "databricks") {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "#fff5f3", border: "1px solid #ff3621", borderRadius: 12, padding: "2px 8px 2px 4px", fontSize: "0.65rem", fontWeight: 600, color: "#e02f1d" }}>
        <DatabricksLogo size={14} /> DBX
      </span>
    );
  }
  return null;
}

const styles = `
  .flow-container {
    display: flex;
    align-items: flex-start;
    gap: 0;
    overflow-x: auto;
    padding: 24px 16px;
    min-height: 180px;
  }
  .flow-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 150px;
    max-width: 170px;
    flex-shrink: 0;
  }
  .flow-box {
    width: 150px;
    min-height: 120px;
    border-radius: 10px;
    padding: 14px 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 8px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    cursor: pointer;
    position: relative;
    user-select: none;
  }
  .flow-box:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  }
  .flow-box.selected {
    box-shadow: 0 0 0 3px #0972d3, 0 4px 16px rgba(9,114,211,0.2);
  }
  .flow-box.pending {
    background: #f4f4f4;
    border: 2px dashed #aab7b8;
  }
  .flow-box.running {
    background: #fff;
    border: 2px solid #0972d3;
    box-shadow: 0 0 0 3px rgba(9,114,211,0.15), 0 4px 12px rgba(9,114,211,0.1);
    animation: pulse 1.5s infinite;
  }
  .flow-box.completed {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border: 2px solid #1d8102;
  }
  .flow-box.blocked {
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border: 2px solid #d13212;
  }
  .flow-box.aws {
    border-top: 4px solid #0972d3;
  }
  .flow-box.databricks {
    border-top: 4px solid #ff3621;
  }
  .flow-box-title {
    font-weight: 700;
    font-size: 0.8rem;
    color: #16191f;
  }
  .flow-box-status {
    font-size: 0.7rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .flow-box-status.running { color: #0972d3; }
  .flow-box-status.completed { color: #1d8102; }
  .flow-box-status.blocked { color: #d13212; }
  .flow-box-status.pending { color: #aab7b8; }
  .flow-box-message {
    font-size: 0.68rem;
    color: #5f6b7a;
    line-height: 1.3;
    max-height: 32px;
    overflow: hidden;
  }
  .flow-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    padding-top: 40px;
  }
  .flow-arrow svg {
    width: 36px;
    height: 20px;
  }
  .flow-arrow.active path {
    stroke: #0972d3;
    animation: arrowPulse 1s infinite;
  }
  .flow-arrow.done path {
    stroke: #1d8102;
  }
  .flow-arrow.inactive path {
    stroke: #d1d5db;
  }
  .flow-platform-badge {
    position: absolute;
    top: -10px;
    right: -6px;
  }
  .detail-panel {
    margin-top: 20px;
    border: 1px solid #e9ebed;
    border-radius: 10px;
    padding: 20px;
    background: #fafbfc;
    animation: slideDown 0.2s ease-out;
  }
  .detail-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e9ebed;
  }
  .detail-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #5f6b7a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .detail-value {
    font-size: 0.9rem;
    color: #16191f;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(9,114,211,0.15), 0 4px 12px rgba(9,114,211,0.1); }
    50% { box-shadow: 0 0 0 6px rgba(9,114,211,0.1), 0 4px 16px rgba(9,114,211,0.15); }
  }
  @keyframes arrowPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const PIPELINE_STAGES = [
  { key: "guardrail_input", label: "Input\nGuardrail", platform: "aws", icon: "🛡️" },
  { key: "supervisor", label: "Supervisor", platform: "aws", icon: "🧠" },
  { key: "data_analyst", label: "Data\nAnalyst", platform: "databricks", icon: "📊" },
  { key: "validator", label: "Validator", platform: "databricks", icon: "✅" },
  { key: "guardrail_output", label: "Output\nGuardrail", platform: "aws", icon: "🛡️" },
  { key: "synthesizer", label: "Synthesizer", platform: "aws", icon: "📝" },
];

function getStageEvents(stageKey, events) {
  return events.filter((e) => {
    if (stageKey === "guardrail_input" && e.type === "guardrail_input") return true;
    if (stageKey === "guardrail_output" && e.type === "guardrail_output") return true;
    if (stageKey === "supervisor" && e.type === "supervisor") return true;
    if (stageKey === "data_analyst" && e.type === "agent_invoke" && e.agent === "Data Analyst") return true;
    if (stageKey === "validator" && e.type === "agent_invoke" && e.agent === "Validator") return true;
    if (stageKey === "synthesizer" && e.type === "agent_invoke" && e.agent === "Synthesizer") return true;
    return false;
  });
}

function getStageStatus(stageKey, events) {
  const relevant = getStageEvents(stageKey, events);
  if (relevant.length === 0) return { status: "pending", message: "" };

  const last = relevant[relevant.length - 1];
  let status = "pending";

  if (last.status === "completed" || last.status === "passed" || last.status === "planned") {
    status = "completed";
  } else if (last.status === "blocked") {
    status = "blocked";
  } else if (last.status === "running" || last.status === "checking" || last.status === "planning") {
    status = "running";
  }

  return { status, message: last.message || "" };
}

function Arrow({ state }) {
  return (
    <div className={`flow-arrow ${state}`}>
      <svg viewBox="0 0 36 20" fill="none">
        <path d="M2 10 L28 10 M22 4 L28 10 L22 16" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function FlowNode({ stage, stageState, isSelected, onClick }) {
  const { status, message } = stageState;

  return (
    <div className="flow-node" onClick={onClick}>
      <div className={`flow-box ${status} ${stage.platform} ${isSelected ? "selected" : ""}`}>
        <div className="flow-platform-badge">
          <PlatformBadge platform={stage.platform} />
        </div>
        <div style={{ fontSize: "1.4rem" }}>{stage.icon}</div>
        <div className="flow-box-title">{stage.label}</div>
        <div className={`flow-box-status ${status}`}>
          {status === "running" && <Spinner size="small" />}
          {status}
        </div>
        {message && <div className="flow-box-message">{message.substring(0, 40)}</div>}
      </div>
    </div>
  );
}

function DetailPanel({ stage, events, onClose }) {
  const stageEvents = getStageEvents(stage.key, events);
  if (stageEvents.length === 0) return null;

  const last = stageEvents[stageEvents.length - 1];

  return (
    <div className="detail-panel">
      <div className="detail-panel-header">
        <SpaceBetween direction="horizontal" size="xs">
          <Box variant="h4">{stage.icon} {stage.label.replace("\n", " ")}</Box>
          <PlatformBadge platform={stage.platform} />
        </SpaceBetween>
        <span onClick={onClose} style={{ cursor: "pointer", fontSize: "1.2rem", color: "#5f6b7a" }}>✕</span>
      </div>

      <ColumnLayout columns={2} variant="text-grid">
        {last.message && (
          <div>
            <div className="detail-label">Status Message</div>
            <div className="detail-value">{last.message}</div>
          </div>
        )}

        {last.task && (
          <div>
            <div className="detail-label">Task</div>
            <div className="detail-value">{last.task}</div>
          </div>
        )}

        {last.route && (
          <div>
            <div className="detail-label">Route</div>
            <div className="detail-value">{last.route}</div>
          </div>
        )}

        {last.status && (
          <div>
            <div className="detail-label">Status</div>
            <div className="detail-value">{last.status}</div>
          </div>
        )}
      </ColumnLayout>

      {last.subtasks && (
        <div style={{ marginTop: 16 }}>
          <div className="detail-label">Execution Plan ({last.subtasks.length} steps)</div>
          <div style={{ marginTop: 8 }}>
            {last.subtasks.map((st) => (
              <div key={st.id} style={{ padding: "6px 0", borderBottom: "1px solid #e9ebed", fontSize: "0.85rem" }}>
                <strong>{st.id}</strong>: <span style={{ color: "#0972d3" }}>[{st.agent}]</span> {st.task}
                {st.depends_on.length > 0 && <span style={{ color: "#5f6b7a" }}> → depends on: {st.depends_on.join(", ")}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {last.result_preview && (
        <div style={{ marginTop: 16 }}>
          <div className="detail-label">Result</div>
          <div className="detail-value" style={{ background: "#fff", border: "1px solid #e9ebed", borderRadius: 6, padding: 12, marginTop: 6 }}>
            {last.result_preview}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AgentFlowVisualization({ events, isRunning }) {
  const [selectedStage, setSelectedStage] = useState(null);

  const stageStates = useMemo(() => {
    return PIPELINE_STAGES.map((stage) => ({
      stage,
      state: getStageStatus(stage.key, events),
    }));
  }, [events]);

  const handleNodeClick = (stage) => {
    setSelectedStage(selectedStage?.key === stage.key ? null : stage);
  };

  return (
    <Container
      header={
        <Header
          variant="h3"
          description="Click any step to view full details below"
          actions={isRunning ? <Spinner /> : null}
        >
          Agent Execution Flow
        </Header>
      }
    >
      <style>{styles}</style>
      <div className="flow-container">
        {stageStates.map((item, i) => {
          const arrowState =
            item.state.status === "completed"
              ? "done"
              : item.state.status === "running"
              ? "active"
              : "inactive";

          return (
            <React.Fragment key={item.stage.key}>
              <FlowNode
                stage={item.stage}
                stageState={item.state}
                isSelected={selectedStage?.key === item.stage.key}
                onClick={() => handleNodeClick(item.stage)}
              />
              {i < stageStates.length - 1 && <Arrow state={arrowState} />}
            </React.Fragment>
          );
        })}
      </div>

      {selectedStage && (
        <DetailPanel
          stage={selectedStage}
          events={events}
          onClose={() => setSelectedStage(null)}
        />
      )}
    </Container>
  );
}
