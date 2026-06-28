import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { Accounts } from './pages/Accounts';
import { Proxies } from './pages/Proxies';
import { QuickActions } from './pages/QuickActions';
import { useStore } from './stores/useStore';

function App() {
  const { currentPage, sidebarOpen } = useStore();

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'accounts':
        return <Accounts />;
      case 'proxies':
        return <Proxies />;
      case 'quick-actions':
        return <QuickActions />;
      default:
        return <PlaceholderPage title={currentPage} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#1a1a2e]">
      <Sidebar />
      <div className={`transition-all duration-300 ${sidebarOpen ? 'ml-56' : 'ml-16'}`}>
        <Header />
        <main className="min-h-[calc(100vh-3.5rem)]">{renderPage()}</main>
      </div>
    </div>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-slate-100 mb-4 capitalize">{title}</h1>
      <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-8 text-center">
        <p className="text-slate-400">
          This page is under development. Coming in the next update.
        </p>
      </div>
    </div>
  );
}

export default App;
