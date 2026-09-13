function isAllowedExternalUrl(value) {
  try {
    const parsedUrl = new URL(value);
    return (
      (parsedUrl.protocol === "https:" || parsedUrl.protocol === "http:") &&
      !parsedUrl.username &&
      !parsedUrl.password
    );
  } catch {
    return false;
  }
}

module.exports = {
  isAllowedExternalUrl,
};
