import { ToastContainer } from '../components/ui';
import { AppRoutes } from './routes';
import { Providers } from './providers';

export const App = () => {
  return (
    <Providers>
      <AppRoutes />
      <ToastContainer />
    </Providers>
  );
};

export default App;
