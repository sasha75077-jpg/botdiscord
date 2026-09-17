import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

export const useAuth = () => {
  const { user, isAuthenticated, logout } = useAuthStore();

  return {
    user,
    isAuthenticated,
    isOwner: user?.role === 'owner',
    isAdmin: user?.role === 'admin' || user?.role === 'owner',
    logout,
  };
};

export const useRequireAuth = (requiredRole?: 'owner' | 'admin') => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (requiredRole === 'owner' && user?.role !== 'owner') {
      navigate('/');
    } else if (requiredRole === 'admin' && !['owner', 'admin'].includes(user?.role || '')) {
      navigate('/');
    }
  }, [isAuthenticated, user, requiredRole, navigate]);

  return { user, isAuthenticated };
};
