module.exports = {
  presets: [
    [
      "@babel/preset-env",
      {
        // Без import в начале файлов — скрипты подключаются обычными <script>, не module
        useBuiltIns: false,
        modules: false,
      },
    ],
  ],
};
