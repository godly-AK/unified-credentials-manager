"use client";

interface Transaction {
  id: string;
  from: string;
  to: string;
  amount?: number;
}

interface Props {
  history: Transaction[];
}

export default function TransactionHistory({ history }: Props) {
  return (
    <div className="bg-[#101826] p-5 rounded-xl shadow-[0_0_15px_rgba(0,255,255,0.5)] text-white mt-6">
      <h2 className="text-lg font-semibold mb-3">Transaction History</h2>
      {history.length === 0 ? (
        <p className="text-gray-400 text-sm">No transactions yet.</p>
      ) : (
        <div className="overflow-y-auto max-h-64">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="text-left py-2">From</th>
                <th className="text-left py-2">To</th>
                <th className="text-right py-2">Amount (₹)</th>
              </tr>
            </thead>
            <tbody>
              {history
                .slice()
                .reverse()
                .map((tx) => (
                  <tr key={tx.id} className="border-b border-gray-800">
                    <td className="py-1">{tx.from}</td>
                    <td className="py-1">{tx.to}</td>
                    <td className="text-right py-1">{tx.amount?.toFixed(2)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
