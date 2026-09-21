/**
 * The one admin account. Username and a bcrypt hash come from the environment; no
 * credential is ever imported into a client component.
 */
import { compare } from 'bcryptjs';

export async function checkCredentials(
  username: string,
  password: string,
): Promise<boolean> {
  const expectedUser = process.env.ADMIN_USERNAME;
  const hash = process.env.ADMIN_PASSWORD_HASH;
  if (!expectedUser || !hash) {
    throw new Error('ADMIN_USERNAME and ADMIN_PASSWORD_HASH must be set');
  }
  const userOk = username === expectedUser;
  // Always run the hash comparison, so a wrong username is not faster than a wrong password.
  const passwordOk = await compare(password, hash);
  return userOk && passwordOk;
}
