interface Props {
  balances: Record<string, number>;
}

export default function BalancePanel({ balances }: Props) {
  const users = Object.keys(balances);

  return (
    <div className="bg-[#101826] p-4 rounded-xl shadow-[0_0_15px_rgba(0,255,255,0.5)]">
      <h2 className="text-lg font-semibold mb-2 text-white">User Balances</h2>
      {users.length === 0 && <p className="text-gray-400 text-sm">No users</p>}
      {users.map((user) => (
        <div key={user} className="flex justify-between p-2 mb-1 rounded bg-[#0a0f1a] text-white">
          <span>{user}</span>
          <span>₹{(Number(balances[user]) || 0).toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}
