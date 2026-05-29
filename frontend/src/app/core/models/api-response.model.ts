/** Matches backend `ApiResponse` (watchlist and other v1 endpoints). */
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T | null;
}
