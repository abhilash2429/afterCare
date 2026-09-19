let seen = false;

export function introAlreadySeen() {
  return seen;
}

export function markIntroSeen() {
  seen = true;
}

export function resetIntro() {
  seen = false;
}
