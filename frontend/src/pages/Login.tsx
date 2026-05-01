import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { setToken } from "../api/client";
import { authApi } from "../api/resources";
import { Notice } from "../components/Status";
import { errorMessage } from "../hooks";

export function Login({ onLogin }: { onLogin: () => Promise<void> }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("12345678");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await authApi.login(email, password);
      setToken(response.access_token);
      await onLogin();
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "login"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div>
          <span className="eyebrow">Biblioteca Digital</span>
          <h1>Biblioteca Digital</h1>
          <p>Console operacional para catálogo, empréstimos, solicitações e notificações.</p>
        </div>
        {error ? <Notice tone="error">{error}</Notice> : null}
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="seu@email.com" required />
        </label>
        <label>
          Senha
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" placeholder="Sua senha" required />
        </label>
        <button className="primary" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
