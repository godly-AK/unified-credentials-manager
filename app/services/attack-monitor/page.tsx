"use client";

import { useEffect, useMemo, useState } from "react";
import NodeGraph, { Node, Transaction } from "./NodeGraph";
import TransactionPanel from "./TransactionPanel";
import BreachPanel from "./BreachPanel";
import BalancePanel from "./BalancePanel";
import TransactionHistory from "./TransactionHistory"; // new import

type User = {
  username: string;
  x: number;
  y: number;
};

interface Props {
  loggedInUsers?: User[];
}

export default function AttackMonitorPage({ loggedInUsers = [] }: Props) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [transactionHistory, setTransactionHistory] = useState<Transaction[]>([]); // new state

  // init
  useEffect(() => {
    const users =
      loggedInUsers.length > 0
        ? loggedInUsers
        : [
            { username: "Arpan", x: 50, y: 100 },
            { username: "Adarsh", x: 250, y: 200 },
            { username: "Angela", x: 200, y: 300 },
            { username: "Meenakshi", x: 350, y: 100 },
            { username: "Suraj", x: 300, y: 300 },
          ];

    const initialNodes: Node[] = users.map((u) => ({
      id: u.username,
      x: u.x,
      y: u.y,
      status: "safe",
    }));

    const initialBalances: Record<string, number> = {};
    users.forEach((u) => (initialBalances[u.username] = 1000));

    setNodes(initialNodes);
    setBalances(initialBalances);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // connections = fully connected mesh
  const connections = useMemo(() => {
    const conns: Record<string, string[]> = {};
    nodes.forEach((n) => {
      conns[n.id] = nodes.filter((m) => m.id !== n.id).map((m) => m.id);
    });
    return conns;
  }, [nodes]);

  // breach handler
  const handleBreach = (breachedId: string) => {
    setNodes((prev) =>
      prev.map((node) => {
        if (node.id === breachedId) return { ...node, status: "breached" };
        if ((connections[breachedId] || []).includes(node.id) && node.status !== "breached")
          return { ...node, status: "risk" };
        return node;
      })
    );
  };

  // transaction handler
  const handleTransaction = (from: string, to: string, amount: number) => {
    if (!(from in balances) || !(to in balances)) {
      alert("Invalid users");
      return;
    }
    if (balances[from] < amount) {
      alert(`${from} has insufficient balance!`);
      return;
    }

    // update balances
    setBalances((prev) => ({
      ...prev,
      [from]: prev[from] - amount,
      [to]: prev[to] + amount,
    }));

    // create transaction
    const txId = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    const tx: Transaction = { id: txId, from, to, amount };

    // add to animation and history
    setTransactions((prev) => [...prev, tx]);
    setTransactionHistory((prev) => [...prev, tx]);

    // mark nodes temporarily as 'risk'
    setNodes((prev) =>
      prev.map((n) => {
        if (n.id === from || n.id === to) {
          if (n.status === "breached") return n;
          return { ...n, status: "risk" };
        }
        return n;
      })
    );

    // revert after animation
    setTimeout(() => {
      setTransactions((prev) => prev.filter((t) => t.id !== txId));

      const breachedIds = nodes.filter((n) => n.status === "breached").map((n) => n.id);

      setNodes((prevNodes) =>
        prevNodes.map((node) => {
          if (node.status === "breached") return node;
          const shouldBeRisk = breachedIds.some((bid) => (connections[bid] || []).includes(node.id));
          return { ...node, status: shouldBeRisk ? "risk" : "safe" };
        })
      );
    }, 1100);
  };

  // Trigger breach button
  const triggerRandomBreach = () => {
    if (nodes.length === 0) return;
    const safeNodes = nodes.filter((n) => n.status === "safe");
    const target = safeNodes.length ? safeNodes[Math.floor(Math.random() * safeNodes.length)] : nodes[0];
    handleBreach(target.id);
  };

  return (
    <div className="flex p-6 gap-6">
      {/* Network Graph */}
      <div className="flex-1 bg-[#101826] rounded-xl shadow-[0_0_15px_rgba(0,255,255,0.5)] p-4 relative">
        <h2 className="font-semibold mb-2 text-lg text-white">Network Status</h2>
        <p className="text-gray-400 mb-4 text-sm">Click on any node to simulate a breach</p>
        <NodeGraph nodes={nodes} transactions={transactions} onBreach={handleBreach} />
      </div>

      {/* Side Panels */}
      <div className="w-80 flex flex-col gap-4">
        <TransactionPanel balances={balances} triggerTransaction={handleTransaction} />
        <BalancePanel balances={balances} />
        <BreachPanel triggerBreach={triggerRandomBreach} />
        <TransactionHistory history={transactionHistory} /> {/* added */}
      </div>
    </div>
  );
}
