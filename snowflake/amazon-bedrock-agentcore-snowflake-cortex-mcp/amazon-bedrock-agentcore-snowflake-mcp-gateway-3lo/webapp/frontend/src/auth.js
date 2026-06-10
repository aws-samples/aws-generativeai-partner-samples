import { CognitoUserPool, CognitoUser, AuthenticationDetails } from 'amazon-cognito-identity-js';

const POOL_ID = process.env.REACT_APP_COGNITO_POOL_ID || '';
const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID || '';

const userPool = new CognitoUserPool({ UserPoolId: POOL_ID, ClientId: CLIENT_ID });

export function signIn(email, password) {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool });
    const authDetails = new AuthenticationDetails({ Username: email, Password: password });
    user.authenticateUser(authDetails, {
      onSuccess: (session) => {
        const payload = session.getIdToken().payload;
        resolve({
          token: session.getAccessToken().getJwtToken(),
          email: payload.email,
          name: payload.name || email,
          role: (payload['cognito:groups'] || ['analyst'])[0],
        });
      },
      onFailure: (err) => reject(err),
      newPasswordRequired: () => resolve({ newPasswordRequired: true, user }),
    });
  });
}

export function completeNewPassword(cognitoUser, newPassword) {
  return new Promise((resolve, reject) => {
    cognitoUser.completeNewPasswordChallenge(newPassword, {}, {
      onSuccess: (session) => {
        const payload = session.getIdToken().payload;
        resolve({
          token: session.getAccessToken().getJwtToken(),
          email: payload.email,
          name: payload.name || payload.email,
          role: (payload['cognito:groups'] || ['analyst'])[0],
        });
      },
      onFailure: (err) => reject(err),
    });
  });
}

export function getCurrentSession() {
  return new Promise((resolve) => {
    const user = userPool.getCurrentUser();
    if (!user) return resolve(null);
    user.getSession((err, session) => {
      if (err || !session?.isValid()) return resolve(null);
      const payload = session.getIdToken().payload;
      resolve({
        token: session.getAccessToken().getJwtToken(),
        email: payload.email,
        name: payload.name || payload.email,
        role: (payload['cognito:groups'] || ['analyst'])[0],
      });
    });
  });
}

export function signOut() {
  const user = userPool.getCurrentUser();
  if (user) user.signOut();
}
