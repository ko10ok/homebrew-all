class Doq < Formula
  include Language::Python::Virtualenv

  desc "Do Query - cli llm client"
  homepage "https://github.com/ko10ok/do"
  url "https://files.pythonhosted.org/packages/4e/a9/4e81c9d78a3e8b555ed4cfc3a2d944fde9f7af4e26384e10ba29bb802ab9/doque-0.0.1.tar.gz"
  sha256 "4db6b09d3b1bc259edca5459f6d2c465908fc72cad4ad7d4b64d26bceb601a8b"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/doq", "--help"
  end
end
