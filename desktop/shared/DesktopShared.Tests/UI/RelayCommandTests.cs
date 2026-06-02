using TTShared.UI;

namespace TTShared.Tests.UI;

public class RelayCommandTests
{
    [Fact]
    public void Execute_ShouldCallAction()
    {
        var called = false;
        var cmd = new RelayCommand(() => called = true);

        cmd.Execute(null);
        Assert.True(called);
    }

    [Fact]
    public void CanExecute_ShouldReturnTrue_WhenNoCondition()
    {
        var cmd = new RelayCommand(() => { });
        Assert.True(cmd.CanExecute(null));
    }

    [Fact]
    public void CanExecute_ShouldReturnConditionResult()
    {
        var cmd = new RelayCommand(() => { }, () => false);
        Assert.False(cmd.CanExecute(null));
    }

    [Fact]
    public void GenericRelayCommand_ShouldPassParameter()
    {
        string? received = null;
        var cmd = new RelayCommand<string>(s => received = s);

        cmd.Execute("hello");
        Assert.Equal("hello", received);
    }

    [Fact]
    public void GenericRelayCommand_CanExecute_WithParameter()
    {
        var cmd = new RelayCommand<string>(_ => { }, s => s == "valid");

        Assert.True(cmd.CanExecute("valid"));
        Assert.False(cmd.CanExecute("invalid"));
    }

    [Fact]
    public void Constructor_ShouldThrow_WhenExecuteNull()
    {
        Assert.Throws<ArgumentNullException>(() => new RelayCommand(null!));
    }

    [Fact]
    public void RaiseCanExecuteChanged_ShouldNotThrow()
    {
        var cmd = new RelayCommand(() => { });
        cmd.RaiseCanExecuteChanged(); // 不应抛出异常
    }
}
