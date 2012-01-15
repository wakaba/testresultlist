#!/usr/bin/perl
use strict;
use warnings;
use Path::Class;
use lib file (__FILE__)->dir->subdir ('modules', 'manakai', 'lib')->stringify;
use lib file (__FILE__)->dir->subdir ('modules', 'perl-charclass', 'lib')->stringify;
use CGI::Carp qw[fatalsToBrowser];

my $data_dir_name = file (__FILE__)->dir->subdir ('data')->absolute . '/';

use Message::CGI::HTTP;
my $cgi = Message::CGI::HTTP->new;

use Message::DOM::DOMImplementation;
my $dom = Message::DOM::DOMImplementation->new;

binmode STDOUT, ':utf8';

my $path = $cgi->path_info;
$path = '' unless defined $path;

my @path = split m#/#, percent_decode ($path), -1;

if (@path == 3 and $path[0] eq '' and $path[1] =~ /\A[0-9a-z-]+\z/) {
  my $table_id = $path[1];
    
  if ($path[2] eq 'all') {
    my $table = get_table ($table_id);
    
    if ($table) {
      my $envs = get_envs ();
      my $tests = $table->{tests} || {};

      print qq[Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML>
<title>Results for @{[htescape ($table->{info}->{label} || $table_id)]}</title>
<link rel=stylesheet href="../../style">
<h1>Results for 
<a href=info>@{[htescape ($table->{info}->{label} || $table_id)]}</a></h1>

<table><thead><tr><th scope=col>Test];

      ## NOTE: Ummm...  We need two-pass process...
      my @envs;
      my %has_env;
      for my $test_id (keys %{$tests}) {
        for my $env_id (keys %{$tests->{$test_id}->{result} or {}}) {
          push @envs, $env_id unless $has_env{$env_id};
          $has_env{$env_id} = 1;
        }
      }
      @envs = sort {$a <=> $b} @envs;

      for my $env_id (@envs) {
        print q[<th scope=col>], htescape ($envs->{$env_id}->{label} ||
                                           $envs->{$env_id}->{name});
      }

      my $stat;
      print q[<tbody>];
      
      for my $test_id (sort {$a cmp $b} keys %{$tests}) {
        print q[<tr><th scope=row>];

        print q[<a href="], htescape ($table->{info}->{url_prefix} || ''),
            htescape ($tests->{$test_id}->{name}), q[">];
        my $label = htescape ($tests->{$test_id}->{label} ||
                              $tests->{$test_id}->{name});
        $label =~ s/\n/<br>/g;
        print $label;
        print q[</a>];
        
        for my $env_id (@envs) {
          my $result = $tests->{$test_id}->{result}->{$env_id};

          unless ($result->{class}) {
            print q[<td>];
            next;
          }

          my $env_label = htescape ($envs->{$env_id}->{label} ||
                                    $envs->{$env_id}->{name});
          my $test_label = htescape ($tests->{$test_id}->{label} ||
                                     $tests->{$test_id}->{name});
          $test_label =~ s/\n/ \n/g;
          
          print q[<td class="];
          print scalar htescape ($result->{class} || '');
          print qq[" title="$env_label \n$test_label">];
          print scalar htescape ($result->{text} || '');

          $stat->{$env_id}->{'class_' . ($result->{class} || '')}++;
          $stat->{$env_id}->{count}++;
        }
      }

      print q[<tfoot>];

      for my $bbb (['class_PASS', 'Passed'],
                   ['class_FAIL', 'Failed'],
                   ['class_SKIPPED', 'Skipped'],
                   ['class_has', 'Has'],
                   ['count', 'Total']) {
        print q[<tr><th scope=row>], htescape ($bbb->[1]);

        for my $env_id (@envs) {
          print q[<td>], (0+$stat->{$env_id}->{$bbb->[0]});
          print ' (', get_percentage ($stat->{$env_id}->{$bbb->[0]},
                                      $stat->{$env_id}->{count}), '%)'
              unless $bbb->[0] eq 'count';
        }
      }
      
      print q[</table>

<footer>[<a href=info>Info</a>]
[<a href=all>All results</a>]</footer>];
      
      exit;
    }
  } elsif ($path[2] eq 'info') {
    if ($cgi->request_method eq 'POST') {
      my $table = get_table ($table_id, lock => 1, create => 1);
      
      $table->{info}->{label} = get_string_parameter ('label');
      $table->{info}->{url_prefix} = get_string_parameter ('url-prefix');

      print qq[Status: 200 Accepted\nContent-Type: text/plain; charset=utf-8\n\n];
      set_table ($table_id, $table);

      exit;
    } else {
      my $table = get_table ($table_id);
      
      print qq[Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML>
<title>Information on
@{[htescape (($table ? $table->{info}->{label} : undef) || $table_id)]}</title>
<link rel=stylesheet href="../../style">
<h1>Information on 
@{[htescape (($table ? $table->{info}->{label} : undef) || $table_id)]}</h1>
];

      unless ($table) {
        print q[<p>This testset is not created yet.];
      }
      
      print qq[<form action=info accept-charset=utf-8 method=post>

<dl>

<dt>Testset ID
<dd><input type=text readonly value="@{[htescape ($table_id)]}">

<dt>Human-readable label
<dd><input type=text name=label
    value="@{[htescape ($table->{info}->{label} || '')]}">

<dt>Testcase URL prefix
<dd><input type=url name=url-prefix
    value="@{[htescape ($table->{info}->{url_prefix} || '')]}">

</dl>

<p><input type=submit value="Save">

</form>

<footer>[<a href=info>Info</a>]
[<a href=all>All results</a>]</footer>];
      
      exit;
    }
  }
} elsif (@path == 2 and $path[0] eq '' and $path[1] =~ /\A[0-9a-z-]+\z/) {
  if ($cgi->request_method eq 'POST') {
    my $table_id = $path[1];
    my $table = get_table ($table_id, lock => 1);
    if ($table) {
      my $envs = get_envs (lock => 1);

      my $env_name = get_string_parameter ('env-name');
      
      my $env;
      my $env_id;
      for (keys %$envs) {
        if ($envs->{$_}->{name} eq $env_name) {
          $env = $envs->{$_};
          $env_id = $_;
          last;
        }
      }
      unless ($env) {
        $env = {name => $env_name};
        $env_id = (time + rand (1)) . '';
        $envs->{$env_id} = $env;
      }
      
      my @test_name = $cgi->get_parameter ('test-name');
      my @test_label = $cgi->get_parameter ('test-label');
      my @test_class = $cgi->get_parameter ('test-class');
      my @test_result = $cgi->get_parameter ('test-result');

      for my $i (0..$#test_name) {
        my $test = $table->{tests}->{$test_name[$i]} ||= {};
        $test->{name} = $test_name[$i] || $test->{name};
        $test->{label} = $test_label[$i] || $test->{label};

        my $result = {class => $test_class[$i],
                      text => Encode::decode ('utf-8', $test_result[$i])};
        $test->{result}->{$env_id} = $result;
      }

      print qq[Status: 200 Accepted\nContent-Type: text/plain; charset=utf-8\n\n];
      set_table ($table_id, $table);
      set_envs ($envs);
      
      exit;
    }
  } else {
    print q[Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML>
<title>List</title>
<ul>
<li><a href=all>all</a>
<li><a href=info>info</a>
</ul>];
    exit;
  }
} elsif (@path == 2 and $path[0] eq '' and $path[1] eq '_dummy_') {
  print "Content-Type: text/plain; charset=utf-8\n\n200";
  exit;
}

print "Status: 404 Not Found\nContent-Type: text/plain\n\n404";
exit;

sub percent_decode ($) {
  return $dom->create_uri_reference ($_[0])
      ->get_iri_reference
      ->uri_reference;
} # percent_decode

sub get_string_parameter ($) {
  my $value = $cgi->get_parameter ($_[0]);
  if (defined $value) {
    require Encode;
    return Encode::decode ('utf-8', $value);
  } else {
    return '';
  }
} # get_string_parameter

sub htescape ($) {
  my $s = shift;
  $s =~ s/&/&amp;/g;
  $s =~ s/</&lt;/g;
  $s =~ s/>/&gt;/g;
  $s =~ s/"/&quot;/g;
  return $s;
} # htescape

sub get_percentage ($$) {
  my ($a, $b) = @_;
  $b ||= 1;
  
  return int (100 * $a / $b);
} # get_percentage

use Storable qw/nstore retrieve/;

sub get_table ($%) {
  my $table_id = shift;
  my %opt = @_;

  my $table_file_name = $data_dir_name . $table_id . '.dat';

  if ($opt{lock}) {
    ## NOTE: This does not allow multiple files locked in the same process.
    our $table_lock;
    my $lock_file_name = $table_file_name . '.lock';
    open $table_lock, '>', $lock_file_name or die "$0: $lock_file_name: $!";
    use Fcntl ':flock';
    flock $table_lock, LOCK_EX;
  }

  if (-f $table_file_name) {
    return retrieve $table_file_name or die "$0: $table_file_name: $!";
  } else {
    if ($opt{create}) {
      return {};
    } else {
      return undef;
    }
  }
} # get_table

sub set_table ($$) {
  my $table_id = shift;
  my $table = shift;
  
  my $table_file_name = $data_dir_name . $table_id . '.dat';
  
  nstore $table, $table_file_name or die "$0: $table_file_name: $!";

  chdir $data_dir_name;
  system '/usr/bin/cvs', 'add', '-kb', $table_file_name;
  system '/usr/bin/cvs', 'commit', '-m', '', $table_file_name;
} # set_table

sub get_envs (%) {
  my %opt = @_;

  ## NOTE: |get_envs| must be invoked after |get_table|, to avoid
  ## deadlocks.

  my $envs_file_name = $data_dir_name . '_test-envs.dat';

  if ($opt{lock}) {
    our $envs_lock;
    my $lock_file_name = $envs_file_name . '.lock';
    open $envs_lock, '>', $lock_file_name or die "$0: $lock_file_name: $!";
    use Fcntl ':flock';
    flock $envs_lock, LOCK_EX;
  }

  if (-f $envs_file_name) {
    return retrieve $envs_file_name or die "$0: $envs_file_name: $!";
  } else {
    return {};
  }
} # get_envs

sub set_envs ($) {
  my $envs = shift;
  
  my $envs_file_name = $data_dir_name . '_test-envs.dat';
  
  nstore $envs, $envs_file_name or die "$0: $envs_file_name: $!";

  chdir $data_dir_name;
  system '/usr/bin/cvs', 'add', '-kb', $envs_file_name;
  system '/usr/bin/cvs', 'commit', '-m', '', $envs_file_name;
} # set_envs
