import { useEffect, useState, ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface AppLayoutProps {
  children: ReactNode;
}

export const AppLayout = ({ children }: AppLayoutProps) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const syncSidebarState = () => {
      setSidebarCollapsed(window.innerWidth < 1024);
    };

    syncSidebarState();
    window.addEventListener('resize', syncSidebarState);

    return () => {
      window.removeEventListener('resize', syncSidebarState);
    };
  }, []);

  return (
    <div className="relative flex h-screen overflow-hidden bg-background text-foreground">
      <div className="pointer-events-none absolute inset-0 bg-shell-radial" aria-hidden="true" />
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto overflow-x-hidden px-3 pb-3 pt-2 sm:px-4 sm:pb-4 lg:px-6 lg:pb-6">
          {children}
        </main>
      </div>
    </div>
  );
};
