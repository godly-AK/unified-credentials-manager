import { useEffect, useState } from "react";

interface Props {
  balances: Record<string, number>;
  triggerTransaction: (from: string, to: string, amount: number) => void;
}

export default function TransactionPanel({ balances, triggerTransaction }: Props) {
  const users = Object.keys(balances);
  const [sender, setSender] = useState<string>(users[0] || "");
  const [recipient, setRecipient] = useState<string>(users[1] || "");
  const [amount, setAmount] = useState<number | "">("");

  useEffect(() => {
    // update controlled selects when user list changes
    const keys = Object.keys(balances);
    setSender((prev) => (keys.includes(prev) ? prev : keys[0] || ""));
    setRecipient((prev) => (keys.includes(prev) ? prev : keys[1] || keys[0] || ""));
  }, [balances]);

  const onSend = () => {
    if (!sender || !recipient) {
      alert("Choose sender and recipient");
      return;
    }
    if (sender === recipient) {
      alert("Sender and recipient must be different");
      return;
    }
    const amt = Number(amount);
    if (!amt || amt <= 0) {
      alert("Enter a valid amount");
      return;
    }
    triggerTransaction(sender, recipient, amt);
    setAmount("");
  };

  return (
    <div className="bg-[#101826] p-4 rounded-xl shadow-[0_0_15px_rgba(0,255,255,0.5)] mb-4">
      <h2 className="text-lg font-semibold mb-2 text-white">Send Transaction</h2>

      <label className="text-gray-300 text-sm">Sender</label>
      <select
        value={sender}
        onChange={(e) => setSender(e.target.value)}
        className="w-full mb-2 p-2 rounded bg-[#0a0f1a] text-white outline-none"
      >
        {users.map((u) => (
          <option key={u} value={u}>
            {u}
          </option>
        ))}
      </select>

      <label className="text-gray-300 text-sm">Recipient</label>
      <select
        value={recipient}
        onChange={(e) => setRecipient(e.target.value)}
        className="w-full mb-2 p-2 rounded bg-[#0a0f1a] text-white outline-none"
      >
        {users.map((u) => (
          <option key={u} value={u}>
            {u}
          </option>
        ))}
      </select>

      <label className="text-gray-300 text-sm">Amount</label>
      <input
        value={amount}
        onChange={(e) => setAmount(e.target.value === "" ? "" : Number(e.target.value))}
        type="number"
        placeholder="Amount"
        className="w-full mb-3 p-2 rounded bg-[#0a0f1a] text-white outline-none"
      />

      <button
        onClick={onSend}
        className="w-full bg-[#00ffff] text-black py-2 rounded-lg font-semibold hover:bg-cyan-300 transition"
      >
        Send
      </button>
    </div>
  );
}
