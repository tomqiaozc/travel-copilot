import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

export function LoginPage() {
  const { user, login, devLogin } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (user) {
      navigate("/", { replace: true });
    }
  }, [user, navigate]);

  useEffect(() => {
    const code = searchParams.get("code");
    if (code) {
      login(code).then(() => navigate("/", { replace: true }));
    }
  }, [searchParams, login, navigate]);

  const handleGoogleLogin = () => {
    const redirectUri = `${window.location.origin}/login`;
    const url =
      `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${GOOGLE_CLIENT_ID}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      `&response_type=code` +
      `&scope=${encodeURIComponent("openid email profile")}` +
      `&access_type=offline`;
    window.location.href = url;
  };

  const handleDevLogin = async () => {
    await devLogin();
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-md text-center max-w-sm w-full">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Travel Copilot</h1>
        <p className="text-gray-500 mb-6">AI-powered travel planning</p>
        <button
          onClick={handleGoogleLogin}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition"
        >
          Sign in with Google
        </button>
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button
            onClick={handleDevLogin}
            className="w-full bg-gray-700 text-white py-3 rounded-lg font-medium hover:bg-gray-800 transition"
          >
            Dev Login (Local Mode)
          </button>
        </div>
      </div>
    </div>
  );
}
