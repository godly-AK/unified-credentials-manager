import React, { memo } from "react";
import { motion } from "framer-motion";

export type Node = {
  id: string;
  x: number;
  y: number;
  status: "safe" | "risk" | "breached";
};

export type Transaction = {
  id: string;
  from: string;
  to: string;
  amount?: number;
};

interface Props {
  nodes: Node[];
  transactions: Transaction[];
  onBreach: (id: string) => void;
}

function NodeGraph({ nodes, transactions = [], onBreach }: Props) {
  const nodeSize = 80; // w-20 h-20 => 80px
  const offset = nodeSize / 2;

  return (
    <div className="flex justify-center items-center h-[70vh] relative">
      <svg className="absolute inset-0 w-full h-full overflow-visible pointer-events-none">
        {/* Only draw animated transaction lines (when a transaction exists) */}
        {transactions.map((t) => {
          const fromNode = nodes.find((n) => n.id === t.from);
          const toNode = nodes.find((n) => n.id === t.to);
          if (!fromNode || !toNode) return null;

          return (
            <motion.line
              key={t.id}
              x1={fromNode.x + offset}
              y1={fromNode.y + offset}
              x2={toNode.x + offset}
              y2={toNode.y + offset}
              stroke="#ffcc00"
              strokeWidth={3}
              initial={{ pathLength: 0, opacity: 1 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.9, ease: "easeInOut" }}
              strokeLinecap="round"
            />
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((node) => {
        const baseClasses =
          "absolute rounded-full w-20 h-20 flex flex-col items-center justify-center cursor-pointer text-sm transition-all duration-300";

        const statusClasses =
          node.status === "breached"
            ? "bg-[#ff4d4d] shadow-[0_0_18px_rgba(255,0,0,0.55)]"
            : node.status === "risk"
            ? "bg-[#ffcc00] shadow-[0_0_18px_rgba(255,204,0,0.45)]"
            : "bg-[#00ffff] shadow-[0_0_15px_rgba(0,255,255,0.5)]";

        return (
          <motion.div
            key={node.id}
            className={`${baseClasses} ${statusClasses}`}
            style={{ top: node.y, left: node.x }}
            whileHover={{ scale: 1.08 }}
            animate={{ scale: node.status === "breached" ? 1.06 : 1 }}
            onClick={() => onBreach(node.id)}
          >
            <div className="text-xs font-semibold text-black">{node.id}</div>
          </motion.div>
        );
      })}
    </div>
  );
}

export default memo(NodeGraph);
