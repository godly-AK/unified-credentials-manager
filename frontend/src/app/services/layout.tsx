import ProtectedRoute from '@/components/ProtectedRoute';


export default function ServicesLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
