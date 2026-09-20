import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { authApi, guildsApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface Guild {
  guild_id: string;
  guild_name: string;
}

export default function GuildSwitcher() {
  const { user, login } = useAuthStore();
  const navigate = useNavigate();
  const [switching, setSwitching] = useState(false);

  const { data: guilds } = useQuery({
    queryKey: ['guilds-list'],
    queryFn: async () => (await guildsApi.list()).data as Guild[],
  });

  if (!user?.guild_id || !Array.isArray(guilds) || guilds.length < 2) {
    return null;
  }

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const gid = e.target.value;
    if (!gid || gid === user.guild_id) return;

    setSwitching(true);
    try {
      const { data } = await authApi.switchGuild(gid);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      const me = await authApi.getCurrentUser();
      login(data.access_token, data.refresh_token, me.data);
      navigate('/');
    } catch (err) {
      console.error('Guild switch error:', err);
    } finally {
      setSwitching(false);
    }
  };

  return (
    <select
      value={user.guild_id}
      onChange={handleChange}
      disabled={switching}
      title="Discord сервер"
      className="input max-w-[220px] text-sm py-2"
    >
      {guilds.map((g) => (
        <option key={g.guild_id} value={g.guild_id}>
          {g.guild_name || g.guild_id}
        </option>
      ))}
    </select>
  );
}
