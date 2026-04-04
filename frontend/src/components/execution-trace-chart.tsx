"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { AgentRunResponse } from "@/lib/api";

const AGENT_FILL: Record<string, string> = {
  implementation: "#22c55e",
  review: "#a855f7",
  risk_profile: "#f97316",
  deployment: "#3b82f6",
  monitor: "#14b8a6",
};

const AGENT_FILL_RUNNING: Record<string, string> = {
  implementation: "#86efac",
  review: "#d8b4fe",
  risk_profile: "#fdba74",
  deployment: "#93c5fd",
  monitor: "#5eead4",
};

const STATUS_FILL: Record<string, string> = {
  failed: "#ef4444",
  pending: "#d1d5db",
};

const formatDuration = (ms: number) => {
  if (ms === 0) return "0s";
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
};

function getBarColor(run: AgentRunResponse): string {
  if (run.status === "failed") return STATUS_FILL.failed;
  if (run.status === "pending") return STATUS_FILL.pending;
  if (run.status === "running") return AGENT_FILL_RUNNING[run.agent_type] || "#93c5fd";
  return AGENT_FILL[run.agent_type] || "#6b7280";
}

interface ChartRow {
  name: string;
  offset: number;
  displayDuration: number;
  realDuration: number;
  run: AgentRunResponse;
}

interface ExecutionTraceChartProps {
  runs: AgentRunResponse[];
}

/* eslint-disable @typescript-eslint/no-explicit-any */
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const data = payload[0]?.payload as ChartRow | undefined;
  if (!data?.run) return null;
  const { run, realDuration } = data;

  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg">
      <div className="font-semibold capitalize mb-1">
        {run.agent_type.replace("_", " ")}
        <span className="ml-2 font-normal opacity-70">{run.model || "sonnet"}</span>
      </div>
      <div className="space-y-0.5 text-muted">
        <div>Duration: <span className="text-foreground">{formatDuration(realDuration)}</span></div>
        <div>Cost: <span className="text-foreground">${(run.cost_usd || 0).toFixed(4)}</span></div>
        <div>Tokens: <span className="text-foreground">{(run.input_tokens || 0).toLocaleString()} / {(run.output_tokens || 0).toLocaleString()}</span></div>
        <div>Status: <span className="text-foreground capitalize">{run.status}</span></div>
      </div>
    </div>
  );
};

const CustomBarLabel = ({ x, y, width, height, index, data }: any) => {
  if (!data || !data[index]) return null;
  const row = data[index] as ChartRow;
  const { run, realDuration } = row;
  const barWidth = width as number;
  const barX = x as number;
  const barY = y as number;
  const barH = height as number;

  if (barWidth < 30) return null;

  const label = run.agent_type.replace("_", " ");
  const capLabel = label.charAt(0).toUpperCase() + label.slice(1);
  const durationStr = formatDuration(realDuration);
  const costStr = `$${(run.cost_usd || 0).toFixed(4)}`;
  const tokensStr = `${(run.input_tokens || 0).toLocaleString()}/${(run.output_tokens || 0).toLocaleString()}`;
  const statusStr = run.status === "running" ? " (live)" : run.status === "pending" ? " (queued)" : "";

  const clipId = `bar-clip-${index}`;
  const midY = barY + barH / 2;
  const topY = midY - 7;
  const botY = midY + 8;

  return (
    <g>
      <defs>
        <clipPath id={clipId}>
          <rect x={barX} y={barY} width={barWidth} height={barH} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        {/* Top-left: agent name */}
        <text x={barX + 10} y={topY} fill="white" fontSize={12} fontWeight={600} dominantBaseline="central" textAnchor="start">
          {capLabel}{statusStr}
        </text>
        {/* Bottom-left: duration */}
        <text x={barX + 10} y={botY} fill="white" fontSize={11} opacity={0.75} dominantBaseline="central" textAnchor="start">
          {durationStr}
        </text>
        {/* Top-right: cost */}
        <text x={barX + barWidth - 10} y={topY} fill="white" fontSize={11} fontWeight={500} opacity={0.9} dominantBaseline="central" textAnchor="end" fontFamily="monospace">
          {costStr}
        </text>
        {/* Bottom-right: tokens */}
        <text x={barX + barWidth - 10} y={botY} fill="white" fontSize={11} opacity={0.65} dominantBaseline="central" textAnchor="end" fontFamily="monospace">
          {tokensStr}
        </text>
      </g>
    </g>
  );
};
/* eslint-enable @typescript-eslint/no-explicit-any */

export function ExecutionTraceChart({ runs }: ExecutionTraceChartProps) {
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    const hasActiveAgents = runs.some(r => r.status === "running" || r.status === "pending");
    if (!hasActiveAgents) return;
    const interval = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [runs]);

  const { chartData, totalDisplay } = useMemo(() => {
    if (runs.length === 0) return { chartData: [], totalDisplay: 0 };

    const sorted = [...runs].sort(
      (a, b) => new Date(a.started_at || 0).getTime() - new Date(b.started_at || 0).getTime()
    );

    const realDurations = sorted.map((run) => {
      const start = run.started_at ? new Date(run.started_at).getTime() : Date.now();
      const end = run.finished_at
        ? new Date(run.finished_at).getTime()
        : run.status === "running" ? currentTime : Date.now();
      return Math.max(end - start, 1000);
    });

    // Enforce minimum bar width: each bar is at least 35% of the max bar
    const maxDuration = Math.max(...realDurations);
    const minDisplay = maxDuration * 0.35;
    const displayDurations = realDurations.map(d => Math.max(d, minDisplay));

    let offset = 0;
    const rows: ChartRow[] = sorted.map((run, i) => {
      const row: ChartRow = {
        name: run.agent_type.replace("_", " "),
        offset,
        displayDuration: displayDurations[i],
        realDuration: realDurations[i],
        run,
      };
      offset += displayDurations[i];
      return row;
    });

    return { chartData: rows, totalDisplay: offset };
  }, [runs, currentTime]);

  const renderLabel = useCallback(
    (props: any) => <CustomBarLabel {...props} data={chartData} />,
    [chartData]
  );

  if (runs.length === 0) {
    return (
      <div className="text-xs text-muted">
        No agent execution yet. Agents are triggered when you move the task to a pipeline stage.
      </div>
    );
  }

  const barHeight = 38;
  const chartHeight = chartData.length * (barHeight + 6) + 30;

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
        barCategoryGap={4}
        barSize={barHeight}
      >
        <XAxis
          type="number"
          domain={[0, totalDisplay]}
          tickFormatter={(val) => formatDuration(val)}
          tick={{ fontSize: 11, fill: "var(--color-muted)" }}
          axisLine={{ stroke: "var(--color-border)" }}
          tickLine={false}
        />
        <YAxis type="category" dataKey="name" hide width={0} />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: "var(--color-surface-hover)", opacity: 0.4 }}
        />
        <Bar dataKey="offset" stackId="waterfall" fill="transparent" radius={0} isAnimationActive={false} />
        <Bar
          dataKey="displayDuration"
          stackId="waterfall"
          radius={[4, 4, 4, 4]}
          label={renderLabel}
          isAnimationActive={false}
        >
          {chartData.map((row, i) => (
            <Cell key={i} fill={getBarColor(row.run)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
