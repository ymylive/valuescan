import { FormEvent, useState } from 'react';
import { type Location, useLocation, useNavigate } from 'react-router-dom';
import { Button, Card, CardContent, CardHeader, Input } from '../../components/ui';
import { adminLogin } from '../../services/adminAuth';
import { toApiError } from '../../services/api';

export const AdminLoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('root');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await adminLogin(username.trim(), password);
      if (!response?.success || !response.token) {
        setError(response?.error || 'Invalid credentials.');
        return;
      }
      localStorage.setItem('token', response.token);
      const state = location.state as { from?: Location } | null;
      const target = state?.from?.pathname || '/admin';
      navigate(target, { replace: true });
    } catch (err) {
      const apiError = toApiError(err);
      setError(apiError.message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-6 py-12">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_55%)]" />
      <Card className="relative z-10 w-full max-w-md border-gray-800 bg-gray-900/90">
        <CardHeader>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Admin Access</p>
            <h1 className="text-2xl font-semibold text-white">ValueScan Control Room</h1>
            <p className="text-sm text-gray-400">Sign in to manage data sources, services, and forecasts.</p>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-wide text-gray-400">Username</label>
              <Input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="root"
                autoComplete="username"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-wide text-gray-400">Password</label>
              <Input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                placeholder="********"
                autoComplete="current-password"
              />
            </div>
            {error && <div className="text-sm text-red-400">{error}</div>}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Authenticating...' : 'Enter Admin Panel'}
            </Button>
            <div className="text-xs text-gray-500">Default credentials: root / Qq159741</div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminLoginPage;

