// This file renders the sign-in page for the Wasla frontend.
// It gives users the first authenticated entry point into the support platform.

import { useEffect, useRef, useState } from "react";
import { login } from "../api";
import waslaLogo from "../assets/wasla-logo-arabic.png";
import loginHero from "../assets/login-hero-ai.png";
import "./Login.css";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const errorTimer = useRef(null);

  useEffect(() => {
    return () => {
      if (errorTimer.current) {
        clearTimeout(errorTimer.current);
      }
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      const data = await login({ email, password });
      console.log("LOGIN RESPONSE:", data);
      onLogin(data.access_token, data.user);
    } catch (err) {
      console.error(err);
      setError("خطأ في ادخال البريد الالكتروني او كلمه المرور");
      if (errorTimer.current) {
        clearTimeout(errorTimer.current);
      }
      errorTimer.current = setTimeout(() => setError(""), 3000);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <section className="login-form-panel">
          <img
            className="login-logo"
            src={waslaLogo}
            alt="Wasla"
          />

          <h1>أهلاً</h1>

          <p className="login-subtitle">
            سجّل الدخول إلى مساحة عمل وَصْلَة الخاصة بك
          </p>

          <form className="login-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="login-email">البريد الإلكتروني</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@wasla.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-password">كلمة المرور</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>

            <button
              className="login-button"
              type="submit"
              disabled={loading}
            >
              {loading ? "جارٍ تسجيل الدخول..." : "تسجيل الدخول"}
            </button>
          </form>

          {error && <p className="login-error">{error}</p>}
        </section>

        <section className="login-hero-panel">
          <img
            className="login-hero"
            src={loginHero}
            alt=""
          />
        </section>
      </div>
    </div>
  );
}

export default Login;