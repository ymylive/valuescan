import { Outlet } from 'react-router-dom';
import { AppLayout } from '../../components/layout';

export const AdminLayout = () => {
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
};

export default AdminLayout;

