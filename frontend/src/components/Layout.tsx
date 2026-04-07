import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-blue-600 text-white px-6 py-3 flex justify-between items-center">
        <Link to="/" className="font-bold text-lg">
          Travel Copilot
        </Link>
        {user && (
          <div className="flex items-center gap-4">
            <span className="text-sm">{user.name || user.email}</span>
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.name}
                className="w-8 h-8 rounded-full border-2 border-blue-400"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-blue-800 flex items-center justify-center text-sm font-bold">
                {(user.name || user.email).charAt(0).toUpperCase()}
              </div>
            )}
            <button
              onClick={handleLogout}
              className="text-sm bg-blue-700 px-3 py-1 rounded hover:bg-blue-800"
            >
              Logout
            </button>
          </div>
        )}
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
