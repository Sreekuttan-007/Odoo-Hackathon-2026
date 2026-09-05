import jwt from "jsonwebtoken";
import { env } from "../config/env";

export interface AccessTokenPayload {
  sub: string; // user id
}

export function signAccessToken(userId: string): string {
  return jwt.sign({ sub: userId }, env.SECRET_KEY, {
    expiresIn: `${env.ACCESS_TOKEN_EXPIRE_MINUTES}m`,
  });
}

export function verifyAccessToken(token: string): AccessTokenPayload {
  return jwt.verify(token, env.SECRET_KEY) as AccessTokenPayload;
}
