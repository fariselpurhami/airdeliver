module.exports = {
  hooks: {
    readPackage(pkg) {
      // اعتراض حزمة Tailwind Typography وتصحيح الخطأ الإملائي في شروطها برمجياً
      if (pkg.name === '@tailwindcss/typography') {
        if (pkg.peerDependencies && pkg.peerDependencies.tailwindcss) {
          // استبدال الشرط المكسور بنطاق رقمي سليم
          pkg.peerDependencies.tailwindcss = '>=3.0.0 || >=4.0.0';
        }
      }
      return pkg;
    }
  }
};
