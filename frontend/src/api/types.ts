export type Role = "admin" | "librarian" | "reader";

export type Account = {
  id: number;
  name: string;
  email: string;
  role: Role;
  user_id: number | null;
  is_active: boolean;
};

export type AuthAccount = Pick<Account, "id" | "name" | "email" | "role">;

export type User = {
  id: number;
  name: string;
  email: string;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
};

export type Author = {
  id: number;
  name: string;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
};

export type Book = {
  id: number;
  isbn: string;
  title: string;
  author_id: number;
  author?: Author | null;
  published_date: string;
  is_available: boolean;
  created_at: string;
};

export type Loan = {
  id: number;
  user_id: number;
  book_id: number;
  user?: User | null;
  book?: Book | null;
  loan_date: string;
  expected_return_date: string;
  actual_return_date: string | null;
  fine_value: number;
  status: "active" | "returned";
  renewal_count: number;
};

export type LoanRequest = {
  id: number;
  request_type: "loan" | "return" | "renewal";
  status: "pending" | "approved" | "rejected";
  requester_account_id: number;
  reviewer_account_id: number | null;
  user_id: number;
  book_id: number | null;
  loan_id: number | null;
  rejection_reason: string | null;
  created_at: string;
  reviewed_at: string | null;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  skip: number;
  limit: number;
};

export type LoanMetrics = {
  total_loans: number;
  active_loans: number;
  overdue_loans: number;
  returned_loans: number;
  total_fine_value: number;
  events_by_operation: Record<string, number>;
};

export type Health = {
  status: string;
  database: string;
  redis: string;
};

export type NotificationResponse = {
  total_due_loans: number;
  sent_email_count: number;
  sent_webhook_count: number;
  failed_count: number;
  skipped_count: number;
  deliveries: Array<{
    loan_id: number;
    channel: string;
    status: string;
    skipped: boolean;
    to: string | null;
    subject: string | null;
    error_message: string | null;
    notification_date: string;
  }>;
};
