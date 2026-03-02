import {
  detectNodeColor,
  formatNodeLabel,
  COLOR_MAP,
  COLOR_ICONS,
} from "./nodeCardUtils";
import type { NodeColor } from "./nodeCardUtils";

interface NodeCardProps {
  name: string;
  isEntry: boolean;
  isBranch: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
  isAnimating: boolean;
  isActive: boolean;
  isDone: boolean;
  isDeployed?: boolean;
  onHover: (name: string | null) => void;
  hoveredNode: string | null;
}

const ICON_AREA_W = 36;

interface ServiceIconProps {
  color: NodeColor;
  x: number;
  y: number;
  accent: string;
}

function ServiceIcon({ color, x, y, accent }: ServiceIconProps) {
  return (
    <text
      x={x}
      y={y}
      fontSize={12}
      textAnchor="middle"
      dominantBaseline="middle"
      fill={accent}
      fontFamily="system-ui"
    >
      {COLOR_ICONS[color]}
    </text>
  );
}

interface EntryBadgeProps {
  width: number;
  accent: string;
}

function EntryBadge({ width, accent }: EntryBadgeProps) {
  return (
    <>
      <rect
        x={width - 28}
        y={4}
        width={24}
        height={11}
        rx={5.5}
        fill={accent}
        opacity={0.9}
      />
      <text
        x={width - 16}
        y={9.5}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="white"
        fontSize={6.5}
        fontFamily="Inter, sans-serif"
        fontWeight={700}
      >
        IN
      </text>
    </>
  );
}

export function NodeCard({
  name,
  isEntry,
  isBranch,
  x,
  y,
  width,
  height,
  isAnimating,
  isActive,
  isDone,
  isDeployed = true,
  onHover,
  hoveredNode,
}: NodeCardProps) {
  const color = detectNodeColor(name);
  const { fill, accent, glow } = COLOR_MAP[color];
  const isHovered = hoveredNode === name;

  const opacity = !isDeployed
    ? 0.4
    : isDone
      ? 1
      : isActive
        ? 1
        : isAnimating
          ? 0.5
          : 1;
  const strokeColor = isActive || isHovered ? accent : "rgba(255,255,255,0.08)";
  const strokeWidth = isActive || isHovered ? 1.5 : 1;

  return (
    <g
      transform={`translate(${x},${y})`}
      onMouseEnter={() => onHover(name)}
      onMouseLeave={() => onHover(null)}
      style={{ cursor: "default", opacity }}
      className="animate-node-appear"
    >
      {isActive && (
        <>
          <rect
            x={-3}
            y={-3}
            width={width + 6}
            height={height + 6}
            rx={11}
            fill="none"
            stroke={accent}
            strokeWidth={1.5}
            className="animate-ping"
            style={{ transformOrigin: "center", transformBox: "fill-box" }}
          />
          <rect
            x={-3}
            y={-3}
            width={width + 6}
            height={height + 6}
            rx={11}
            fill="none"
            stroke={glow}
            strokeWidth={2.5}
            className="animate-glow-pulse"
            style={{ transformOrigin: "center", transformBox: "fill-box" }}
          />
        </>
      )}
      <rect
        x={2}
        y={3}
        width={width}
        height={height}
        rx={9}
        fill="rgba(0,0,0,0.35)"
      />
      <rect
        width={width}
        height={height}
        rx={9}
        fill={isEntry ? "rgba(99,102,241,0.15)" : fill}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeDasharray={!isDeployed ? "4 3" : undefined}
      />
      <rect
        width={ICON_AREA_W}
        height={height}
        rx={9}
        fill={accent}
        opacity={0.15}
      />
      <rect
        x={ICON_AREA_W - 1}
        width={1}
        height={height}
        fill={accent}
        opacity={0.2}
      />
      <ServiceIcon
        color={color}
        x={ICON_AREA_W / 2}
        y={height / 2}
        accent={accent}
      />
      <text
        x={(width + ICON_AREA_W) / 2 + 2}
        y={height / 2 + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="rgba(255,255,255,0.88)"
        fontSize={11}
        fontFamily="Inter, sans-serif"
        fontWeight={500}
      >
        {formatNodeLabel(name)}
      </text>
      {isEntry && <EntryBadge width={width} accent={accent} />}
      {isBranch && (
        <text
          x={7}
          y={height - 6}
          fill="#f59e0b"
          fontSize={8}
          fontFamily="Inter, sans-serif"
        >
          ⑂
        </text>
      )}
      {isDone && (
        <text
          x={width - 8}
          y={height - 7}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={accent}
          fontSize={9}
          fontFamily="system-ui"
        >
          ✓
        </text>
      )}
    </g>
  );
}
