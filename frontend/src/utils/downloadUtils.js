export const downloadJsonFile = (data, fileName = "export.json") => {
  if (!data) {
    console.warn("No data available for export");
    return false;
  }

  try {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);

    return true;
  } catch (error) {
    console.error("JSON export failed:", error);
    return false;
  }
};
