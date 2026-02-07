import helpRegistry from "../helpRegistry";

type HelpPanelProps = {
  topicKey: string;
};

export default function HelpPanel({ topicKey }: HelpPanelProps) {
  const topic = helpRegistry[topicKey] ?? helpRegistry.default;

  return (
    <div className="panel help-panel">
      <div className="toolbar">
        <h2>{topic.title}</h2>
      </div>
      <div className="help-body">
        {topic.body.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
    </div>
  );
}
