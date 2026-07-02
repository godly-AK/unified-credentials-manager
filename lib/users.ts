// lib/users.ts
export type User = { username: string; password: string };

// Shared in-memory database
export const users: User[] = [];
