class Doque < Formula
  include Language::Python::Virtualenv

  desc "Do Query - cli llm client"
  homepage "https://github.com/ko10ok/do"
  url "https://files.pythonhosted.org/packages/c1/3b/cd4dbe57e6c4a2562e61a896c4f97102a79565253c4a79b8e43ed7a9d65d/doque-0.2.0.tar.gz"
  sha256 "8ce2e9a3e1f97cca1d4cd9c446d7f3fdb206baf679cd02b848afc661189ecf8e"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/doq", "--help"
  end
end
