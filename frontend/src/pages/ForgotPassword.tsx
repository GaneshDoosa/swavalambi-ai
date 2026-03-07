import { useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, ArrowLeft, Eye, EyeOff } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : "http://localhost:8000/api";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const handleRequestCode = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    
    setLoading(true);
    setError("");
    setSuccessMessage("");
    
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password?email=${encodeURIComponent(email)}`, {
        method: "POST",
      });
      
      const data = await res.json();
      
      if (!res.ok) { 
        setError(data.detail || "Failed to send reset code. Please try again."); 
        return; 
      }
      
      setSuccessMessage(data.message || "Password reset code sent to your email.");
      setStep(2);
    } catch {
      setError("Failed to send reset code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!verificationCode.trim()) { 
      setError("Please enter the verification code."); 
      return; 
    }
    if (!newPassword.trim() || newPassword.length < 8) {
      setError("Password must be at least 8 characters."); 
      return;
    }
    
    setLoading(true);
    setError("");
    
    try {
      const res = await fetch(`${API_BASE}/auth/reset-password?email=${encodeURIComponent(email)}&code=${encodeURIComponent(verificationCode)}&new_password=${encodeURIComponent(newPassword)}`, {
        method: "POST",
      });
      
      const data = await res.json();
      
      if (!res.ok) { 
        setError(data.detail || "Failed to reset password. Please check your code and try again."); 
        return; 
      }
      
      // Password reset successfully, navigate to login
      navigate("/login", { state: { usr: { message: "Password reset successfully. You can now log in with your new password." } } });
    } catch {
      setError("Failed to reset password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-white">
      {/* Header gradient */}
      <header
        className="pt-12 pb-14 px-6 text-center text-white relative"
        style={{ background: "linear-gradient(135deg, #ff8c00 0%, #ffb347 80%, #ffe0b2 100%)" }}
      >
        <div className="absolute left-4 top-12 text-white flex size-10 shrink-0 items-center justify-center cursor-pointer hover:bg-white/10 rounded-full transition-colors">
          <ArrowLeft
            size={24}
            onClick={() => step === 2 ? setStep(1) : navigate(-1)}
          />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight mt-2">Swavalambi</h1>
        <p className="text-sm text-white/80 mt-1">Skills to Self-Reliance</p>
      </header>

      <section className="flex-1 bg-white px-6 pt-8 rounded-t-3xl -mt-6 overflow-y-auto shadow-[0_-4px_24px_rgba(0,0,0,0.08)]">
        {/* Title */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-800">
            {step === 1 ? "Forgot Password" : "Reset Password"}
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            {step === 1
              ? "Enter your email to receive a password reset code."
              : `Enter the code sent to ${email} and your new password.`}
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-xl">
            {error}
          </div>
        )}

        {successMessage && step === 2 && (
          <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm p-3 rounded-xl transition-all">
            {successMessage}
          </div>
        )}

        {step === 1 ? (
          <form className="space-y-5" onSubmit={handleRequestCode}>
            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-widest pl-1">
                Email Address <span className="text-primary">*</span>
              </label>
              <div className="relative">
                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  className="w-full pl-11 pr-4 py-3.5 border border-transparent rounded-xl outline-none bg-gray-50 text-gray-800 focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all text-base"
                  placeholder="you@example.com"
                  required 
                  type="email"
                  inputMode="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError("");
                  }}
                />
              </div>
            </div>

            <div className="pt-4">
              <button
                type="submit" disabled={loading}
                className="bg-primary hover:bg-primary-dark text-white w-full py-4 rounded-xl font-bold text-lg shadow-md active:scale-[0.98] transition-all disabled:opacity-60 flex justify-center items-center"
              >
                {loading ? "Sending Code…" : "Send Reset Code →"}
              </button>
            </div>
          </form>
        ) : (
          <form className="space-y-5" onSubmit={handleResetPassword}>
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-widest pl-1">
                Verification Code <span className="text-primary">*</span>
              </label>
              <div className="relative">
                <input
                  className="w-full px-4 py-3.5 border border-transparent rounded-xl outline-none bg-gray-50 text-gray-800 text-center text-2xl font-bold tracking-widest focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                  maxLength={6}
                  placeholder="• • • • • •"
                  inputMode="numeric"
                  value={verificationCode}
                  onChange={(e) => {
                    setVerificationCode(e.target.value.replace(/\D/g, ""));
                    setError("");
                  }}
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-widest pl-1">
                New Password <span className="text-primary">*</span>
              </label>
              <div className="relative">
                <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  className="w-full pl-11 pr-12 py-3.5 border border-transparent rounded-xl outline-none bg-gray-50 text-gray-800 focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all text-base"
                  placeholder="At least 8 characters"
                  required 
                  type={showPassword ? "text" : "password"}
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    setError("");
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              <p className="text-[11px] text-gray-400 pl-1">Must be at least 8 characters</p>
            </div>

            <div className="pt-4 flex flex-col gap-3">
              <button
                type="submit" disabled={loading}
                className="bg-primary hover:bg-primary-dark text-white w-full py-4 rounded-xl font-bold text-lg shadow-md active:scale-[0.98] transition-all disabled:opacity-60 flex justify-center items-center"
              >
                {loading ? "Resetting Password…" : "Reset Password"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep(1);
                  setVerificationCode("");
                  setNewPassword("");
                  setError("");
                  setSuccessMessage("");
                }}
                disabled={loading}
                className="w-full bg-gray-50 text-gray-600 py-3.5 rounded-xl font-semibold hover:bg-gray-100 transition-all active:scale-[0.98]"
              >
                ← Back to Email
              </button>
            </div>
          </form>
        )}

        <footer className="text-center mt-8 pb-10">
          <p className="text-sm text-gray-500">
            Remember your password?{" "}
            <Link to="/login" className="text-primary font-bold hover:underline">
              Log In
            </Link>
          </p>
        </footer>
      </section>
    </div>
  );
}
