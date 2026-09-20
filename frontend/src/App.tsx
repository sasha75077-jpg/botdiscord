import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

// Pages
import LoginPage from '@/pages/LoginPage';
import DiscordCallbackPage from '@/pages/DiscordCallbackPage';
import OwnerDashboard from '@/pages/owner/Dashboard';
import OwnerSettingsPage from '@/pages/owner/SettingsPage';
import RolesPage from '@/pages/RolesPage';
import ShowcasePage from '@/pages/ShowcasePage';
import ShowcaseManagePage from '@/pages/owner/ShowcaseManagePage';
import AdminDashboard from '@/pages/admin/Dashboard';
import GoogleSheetsSettingsPage from '@/pages/admin/GoogleSheetsSettingsPage';
import UserDashboard from '@/pages/user/Dashboard';
import NewContractPage from '@/pages/contracts/NewContractPage';
import NewApplicationPage from '@/pages/applications/NewApplicationPage';
import ApplicationsPage from '@/pages/applications/ApplicationsPage';
import ApplicationDetailPage from '@/pages/applications/ApplicationDetailPage';
import ContractsPage from '@/pages/contracts/ContractsPage';
import ContractDetailPage from '@/pages/contracts/ContractDetailPage';
import NotificationsPage from '@/pages/admin/NotificationsPage';
import PricesPage from '@/pages/PricesPage';
import BonusPage from '@/pages/BonusPage';
import ProfilePage from '@/pages/ProfilePage';

// Layouts
import OwnerLayout from '@/layouts/OwnerLayout';
import AdminLayout from '@/layouts/AdminLayout';
import UserLayout from '@/layouts/UserLayout';

function App() {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<DiscordCallbackPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Stranger: только витрина серверов
  if (user?.role === 'stranger') {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<DiscordCallbackPage />} />
        <Route path="*" element={<ShowcasePage />} />
      </Routes>
    );
  }

  // Owner routes
  if (user?.role === 'owner') {
    return (
      <OwnerLayout>
        <Routes>
          <Route path="/" element={<OwnerDashboard />} />
          <Route path="/owner/settings" element={<OwnerSettingsPage />} />
          <Route path="/owner/showcase" element={<ShowcaseManagePage />} />
          <Route path="/prices" element={<PricesPage />} />
          <Route path="/guilds/:guildId/roles" element={<RolesPage />} />
          <Route path="/guilds" element={<div>Guilds Management</div>} />
          <Route path="/guilds/:guildId" element={<div>Guild Details</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </OwnerLayout>
    );
  }

  // Admin routes
  if (user?.role === 'admin') {
    return (
      <AdminLayout>
        <Routes>
          <Route path="/" element={<AdminDashboard />} />
          <Route path="/guilds/:guildId" element={<AdminDashboard />} />
          <Route path="/guilds/:guildId/sheets" element={<GoogleSheetsSettingsPage />} />
          <Route path="/guilds/:guildId/roles" element={<RolesPage />} />
          <Route path="/roles" element={<RolesPage />} />
          <Route path="/contracts" element={<ContractsPage />} />
          <Route path="/contracts/new" element={<NewContractPage />} />
          <Route path="/contracts/:id" element={<ContractDetailPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/applications/new" element={<NewApplicationPage />} />
          <Route path="/applications/:id" element={<ApplicationDetailPage />} />
          <Route path="/reports" element={<BonusPage />} />
          <Route path="/users" element={<div>Users</div>} />
          <Route path="/users" element={<div>Users</div>} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/prices" element={<PricesPage />} />
          <Route path="/settings" element={<div>Settings</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AdminLayout>
    );
  }

  // Recruiter routes
  if (user?.role === 'recruiter') {
    return (
      <UserLayout>
        <Routes>
          <Route path="/" element={<UserDashboard />} />
          <Route path="/contracts" element={<ContractsPage />} />
          <Route path="/contracts/new" element={<NewContractPage />} />
          <Route path="/contracts/:id" element={<ContractDetailPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/applications/new" element={<NewApplicationPage />} />
          <Route path="/applications/:id" element={<ApplicationDetailPage />} />
          <Route path="/prices" element={<PricesPage />} />
          <Route path="/reports" element={<BonusPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </UserLayout>
    );
  }

  // User routes
  return (
    <UserLayout>
      <Routes>
        <Route path="/" element={<UserDashboard />} />
        <Route path="/contracts" element={<ContractsPage />} />
        <Route path="/contracts/new" element={<NewContractPage />} />
        <Route path="/contracts/:id" element={<ContractDetailPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/applications/new" element={<NewApplicationPage />} />
        <Route path="/applications/:id" element={<ApplicationDetailPage />} />
        <Route path="/prices" element={<PricesPage />} />
        <Route path="/reports" element={<BonusPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </UserLayout>
  );
}

export default App;
