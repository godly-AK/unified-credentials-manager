declare module 'zxcvbn' {
  export interface ZxcvbnResult {
    score: 0 | 1 | 2 | 3 | 4;
  }

  export default function zxcvbn(password: string, userInputs?: string[]): ZxcvbnResult;
}
