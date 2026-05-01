import { api, pageParams } from "./client";
import type {
  Account,
  AuthAccount,
  Author,
  Book,
  Health,
  Loan,
  LoanMetrics,
  LoanRequest,
  NotificationResponse,
  Paginated,
  User,
} from "./types";

export const authApi = {
  login: (email: string, password: string) =>
    api<{ access_token: string; token_type: "bearer"; expires_in: number; account: AuthAccount }>("/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<Account>("/auth/me"),
};

export const healthApi = {
  get: () => api<Health>("/health", { auth: false }),
};

export const metricsApi = {
  loans: () => api<LoanMetrics>("/metrics/loans"),
  exportLoansCsv: () => api<string>("/metrics/loans/export.csv"),
};

export const userApi = {
  list: (page = 0) => api<Paginated<User>>("/users/", {}, pageParams(page)),
  create: (payload: { name: string; email: string }) =>
    api<User>("/users/", { method: "POST", body: JSON.stringify(payload) }),
  loans: (userId: number) => api<Paginated<Loan>>(`/users/${userId}/loans`),
};

export const authorApi = {
  list: (page = 0) => api<Paginated<Author>>("/authors/", {}, pageParams(page)),
  create: (payload: { name: string }) => api<Author>("/authors/", { method: "POST", body: JSON.stringify(payload) }),
};

export const bookApi = {
  list: (page = 0) => api<Paginated<Book>>("/books/", {}, pageParams(page)),
  create: (payload: { isbn: string; author_id: number; title: string; published_date: string }) =>
    api<Book>("/books/", { method: "POST", body: JSON.stringify(payload) }),
  count: (isbn: string) =>
    api<{ isbn: string; available_exemplars: number; is_available: boolean; message: string }>(`/books/count/${isbn}`),
  exemplars: (isbn: string) => api<Book[]>(`/books/exemplars/${isbn}`),
};

export const loanApi = {
  list: (page = 0, params: { status?: string; user_id?: number; overdue?: boolean } = {}) =>
    api<Paginated<Loan>>("/loans/", {}, { ...pageParams(page), ...params }),
  active: () => api<Paginated<Loan>>("/loans/active"),
  overdue: () => api<Paginated<Loan>>("/loans/overdue"),
  create: (userId: number, bookId: number) =>
    api<Loan>("/loans/", { method: "POST" }, { user_id: userId, book_id: bookId }),
  returnLoan: (loanId: number) => api<Loan>(`/loans/${loanId}/return`, { method: "PUT" }),
};

export const requestApi = {
  list: (page = 0, params: { status?: string; type?: string } = {}) =>
    api<Paginated<LoanRequest>>("/loan-requests/", {}, { ...pageParams(page), ...params }),
  createLoan: (bookId: number) => api<LoanRequest>("/loan-requests/", { method: "POST", body: JSON.stringify({ book_id: bookId }) }),
  createReturn: (loanId: number) =>
    api<LoanRequest>("/return-requests/", { method: "POST", body: JSON.stringify({ loan_id: loanId }) }),
  createRenewal: (loanId: number) =>
    api<LoanRequest>("/renewal-requests/", { method: "POST", body: JSON.stringify({ loan_id: loanId }) }),
  approve: (requestId: number) => api<LoanRequest>(`/loan-requests/${requestId}/approve`, { method: "POST" }),
  reject: (requestId: number, reason: string) =>
    api<LoanRequest>(`/loan-requests/${requestId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
};

export const notificationApi = {
  send: (daysAhead: number, channel: string) =>
    api<NotificationResponse>("/notifications/due-loans/send", { method: "POST" }, { days_ahead: daysAhead, channel }),
};
