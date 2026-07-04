// app/services/page.tsx
'use client';

import React from 'react';
import Link from 'next/link';

const ServicesPage = () => {
  return (
    <div className="p-8 max-w-4xl mx-auto">
    <h1 className="text-3xl font-bold mb-6 text-green-400">Our Services</h1>

    <p className="text-lg mb-4 text-gray-300">
    Welcome to our services section. These are the services we provide:
    </p>

    <ul className="list-disc list-inside space-y-3 text-lg text-gray-200">
    <li>
    <strong>User Registration & Login Security:</strong> Implementing robust authentication systems to safeguard user accounts.
    </li>
    <li>
    <strong>Transaction Threat Detection:</strong> Monitoring and identifying suspicious activities in real-time to prevent financial or data loss.
    </li>
    <li>
    <strong>Anomaly Detection:</strong> Detecting unusual patterns in your network to proactively mitigate potential breaches.
    </li>
    <li>
    <strong>Behavioral Analysis:</strong> Understanding user and system behavior to identify risks before they escalate.
    </li>
    <li>
    <strong>SIEM Tool Integration:</strong> Leveraging advanced Security Information and Event Management solutions for comprehensive threat monitoring and analysis.
    </li>
    </ul>

    <p className="text-lg mt-6 text-gray-300">
    Our mission is to empower organizations with the tools, insights, and expertise they need to stay ahead of password compromises, database breaches, and other cyber threats. With NetKnights by your side, you can focus on growing your business while we safeguard your digital assets.
    </p>

    <div className="mt-6">
    <Link
    href="/services/attack-monitor"
    className="text-cyan-400 hover:underline font-semibold"
    >
    Go to Attack Monitor →
    </Link>
    </div>
    </div>
  );
};

export default ServicesPage;
