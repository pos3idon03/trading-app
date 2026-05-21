import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function AppShell() {
  return (
    <div className="min-h-screen flex bg-surface-950">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto w-full px-4 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
