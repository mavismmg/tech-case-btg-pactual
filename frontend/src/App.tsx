import { useEffect, useState } from "react";
import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { clearToken, getToken } from "./api/client";
import { authApi } from "./api/resources";
import type { Account } from "./api/types";
import { Layout } from "./components/Layout";
import { Notice } from "./components/Status";
import { CatalogPage } from "./pages/Catalog";
import { Dashboard } from "./pages/Dashboard";
import { LoansPage } from "./pages/Loans";
import { Login } from "./pages/Login";
import { MetricsPage } from "./pages/Metrics";
import { NotificationsPage } from "./pages/Notifications";
import { ReaderSpace } from "./pages/ReaderSpace";
import { RequestsPage } from "./pages/Requests";
import { UsersPage } from "./pages/Users";

function StaffRoute({ account, children }: { account: Account; children: ReactElement }) {
  const isStaff = account.role === "admin" || account.role === "librarian";
  return isStaff ? children : <Navigate to="/" replace />;
}

function authenticatedRoutes(account: Account, sessionError: string | null) {
  return (
    <Route path="/" element={<Layout account={account} />}>
      <Route
        index
        element={
          <>
            {sessionError ? <Notice tone="error">{sessionError}</Notice> : null}
            <Dashboard account={account} />
          </>
        }
      />
      <Route path="catalog" element={<CatalogPage account={account} />} />
      <Route path="reader" element={<ReaderSpace userId={account.user_id} />} />
      <Route
        path="users"
        element={
          <StaffRoute account={account}>
            <UsersPage />
          </StaffRoute>
        }
      />
      <Route
        path="loans"
        element={
          <StaffRoute account={account}>
            <LoansPage />
          </StaffRoute>
        }
      />
      <Route
        path="requests"
        element={
          <StaffRoute account={account}>
            <RequestsPage />
          </StaffRoute>
        }
      />
      <Route
        path="metrics"
        element={
          <StaffRoute account={account}>
            <MetricsPage />
          </StaffRoute>
        }
      />
      <Route
        path="notifications"
        element={
          <StaffRoute account={account}>
            <NotificationsPage />
          </StaffRoute>
        }
      />
    </Route>
  );
}

export function App() {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(Boolean(getToken()));
  const [error, setError] = useState<string | null>(null);

  async function loadAccount() {
    if (!getToken()) {
      setLoading(false);
      return;
    }

    try {
      setAccount(await authApi.me());
    } catch {
      clearToken();
      setAccount(null);
      setError("Sessão expirada. Faça login novamente.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAccount();
  }, []);

  if (loading) {
    return <div className="loading-screen">Carregando sessão...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={loadAccount} />} />
      {account ? (
        authenticatedRoutes(account, error)
      ) : (
        <Route path="*" element={<Navigate to="/login" replace />} />
      )}
    </Routes>
  );
}
