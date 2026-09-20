import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

// Pages
import LoginPage from '@/pages/LoginPage';
import DiscordCallbackPage from '@/pages/DiscordCallbackPage';
import OwnerDashboard from '@/pages/owner/Dashboard';
import OwnerSettingsPage from '@/pages/owner/SettingsPage';
import RolesPage from '@/pages/RolesPage';
import AdminDashboard from '@/pages/admin/Dashboard';
import GoogleSheetsSettingsPage from '@/pages/admin/GoogleSheetsSettingsPage';
import UserDashboard from '@/pages/user/Dashboard';
import NewContractPage from '@/pages/contracts/NewContractPage';
import NewApplicationPage from '@/pages/applications/NewApplicationPage';

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

  // Owner routes
  if (user?.role === 'owner') {
    return (
      <OwnerLayout>
        <Routes>
          <Route path="/" element={<OwnerDashboard />} />
          <Route path="/owner/settings" element={<OwnerSettingsPage />} />
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
          <Route path="/contracts" element={<div>Contracts</div>} />
          <Route path="/contracts/new" element={<NewContractPage />} />
          <Route path="/reports" element={<div>Reports</div>} />
          <Route path="/users" element={<div>Users</div>} />
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
          <Route path="/contracts" element={<div>My Contracts (Recruiter)</div>} />
          <Route path="/contracts/new" element={<NewContractPage />} />
          <Route path="/applications" element={<div>Applications (View Only)</div>} />
          <Route path="/applications/new" element={<NewApplicationPage />} />
          <Route path="/profile" element={<div>My Profile</div>} />
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
        <Route path="/contracts" element={<div>My Contracts</div>} />
        <Route path="/contracts/new" element={<NewContractPage />} />
        <Route path="/applications/new" element={<NewApplicationPage />} />
        <Route path="/reports" element={<div>My Reports</div>} />
        <Route path="/profile" element={<div>My Profile</div>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </UserLayout>
  );
}

export default App;
