import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AdminGuard } from './AdminGuard';

const mockAdminCheck = vi.fn();
const mockGetAdminToken = vi.fn();
const mockToApiError = vi.fn();

vi.mock('../../services/adminAuth', () => ({
  adminCheck: () => mockAdminCheck(),
}));

vi.mock('../../services/api', () => ({
  getAdminToken: () => mockGetAdminToken(),
  toApiError: (error: unknown) => mockToApiError(error),
}));

const renderGuard = () => {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route path="/admin/login" element={<div>login-page</div>} />
        <Route
          path="/admin"
          element={(
            <AdminGuard>
              <div>admin-page</div>
            </AdminGuard>
          )}
        />
      </Routes>
    </MemoryRouter>,
  );
};

describe('AdminGuard', () => {
  beforeEach(() => {
    mockAdminCheck.mockReset();
    mockGetAdminToken.mockReset();
    mockToApiError.mockReset();
  });

  it('redirects to login when token is missing', async () => {
    mockGetAdminToken.mockReturnValue('');

    renderGuard();

    await waitFor(() => {
      expect(screen.getByText('login-page')).toBeInTheDocument();
    });
  });

  it('keeps admin page for non-401 check errors when token exists', async () => {
    mockGetAdminToken.mockReturnValue('admin-token');
    mockAdminCheck.mockRejectedValue(new Error('service unavailable'));
    mockToApiError.mockReturnValue({ message: 'service unavailable', status: 503 });

    renderGuard();

    await waitFor(() => {
      expect(screen.getByText('admin-page')).toBeInTheDocument();
    });
    expect(screen.queryByText('login-page')).not.toBeInTheDocument();
  });

  it('redirects to login on 401 check error', async () => {
    mockGetAdminToken.mockReturnValue('expired-token');
    mockAdminCheck.mockRejectedValue(new Error('unauthorized'));
    mockToApiError.mockReturnValue({ message: 'unauthorized', status: 401 });

    renderGuard();

    await waitFor(() => {
      expect(screen.getByText('login-page')).toBeInTheDocument();
    });
  });
});
