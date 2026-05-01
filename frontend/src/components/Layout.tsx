import { Bell, BookOpen, ClipboardList, Home, LogOut, Menu, Users, BarChart3, Library } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { clearToken } from "../api/client";
import type { Account } from "../api/types";
import logoPlaceholder from "../assets/library.webp";
import { formatRole } from "../utils/formatters";

const staffLinks = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/users", label: "Usuários", icon: Users },
  { to: "/catalog", label: "Catálogo", icon: BookOpen },
  { to: "/loans", label: "Empréstimos", icon: ClipboardList },
  { to: "/requests", label: "Solicitações", icon: Library },
  { to: "/metrics", label: "Métricas", icon: BarChart3 },
  { to: "/notifications", label: "Notificações", icon: Bell },
];

const readerLinks = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/catalog", label: "Catálogo", icon: BookOpen },
  { to: "/reader", label: "Meu Espaço", icon: ClipboardList },
];

export function Layout({ account }: { account: Account }) {
  const navigate = useNavigate();
  const isStaff = account.role === "admin" || account.role === "librarian";
  const links = isStaff ? staffLinks : readerLinks;

  function logout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand-mark" src={logoPlaceholder} alt="Biblioteca Digital" />
          <div>
            <strong>Biblioteca</strong>
            <span>Digital</span>
          </div>
        </div>
        <nav>
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink key={link.to} to={link.to} end={link.to === "/"}>
                <Icon size={18} />
                {link.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="mobile-title">
            <Menu size={20} />
            Biblioteca Digital
          </div>
          <div className="account-pill">
            <strong>{account.name}</strong>
            <span>{formatRole(account.role)}</span>
          </div>
          <button type="button" className="icon-button" onClick={logout} title="Sair">
            <LogOut size={18} />
          </button>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
